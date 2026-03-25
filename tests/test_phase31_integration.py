"""Phase 31 integration tests for graceful degradation, hybrid sharing, and progress guidance."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from rd_agent.contracts.exploration import ApproachCategory, FinalSubmissionSnapshot, HypothesisSpec
from rd_agent.contracts.run import ExecutionMode
from rd_agent.contracts.stage import StageKey
from rd_agent.contracts.tool_io import BranchForkRequest, ExploreRoundRequest, RunStartRequest
from rd_agent.orchestration.artifact_state_store import ArtifactStateStore
from rd_agent.orchestration.branch_lifecycle_service import BranchLifecycleService
from rd_agent.orchestration.branch_share_service import BranchShareService
from rd_agent.orchestration.branch_workspace_manager import BranchWorkspaceManager
from rd_agent.orchestration.multi_branch_service import MultiBranchService
from rd_agent.orchestration.operator_guidance import build_finalization_guidance
from rd_agent.orchestration.recovery_service import RecoveryService
from rd_agent.orchestration.run_board_service import RunBoardService
from rd_agent.orchestration.stage_transition_service import StageTransitionService
from rd_agent.ports.embedding_port import EmbeddingUnavailableError
from rd_agent.ports.holdout_port import StubEvaluationPort, StubHoldoutSplitPort


class _ExplodingEmbeddingPort:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingUnavailableError("embedding unavailable")


class _DeterministicEmbeddingPort:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vectors[text] for text in texts]


class _NoopMemoryService:
    def list_memory(self, request):
        return MagicMock(items=[])

    def promote_memory(self, request):
        raise AssertionError("promote_memory should not be called in sharing candidate tests")


class _ScoreByLabelPort:
    def __init__(self, state_store: ArtifactStateStore, scores: dict[str, float]) -> None:
        self._state_store = state_store
        self._scores = scores

    def evaluate(self, *, candidate_node_id: str, fold) -> float:
        node = self._state_store.load_dag_node(candidate_node_id)
        assert node is not None
        branch = self._state_store.load_branch_snapshot(node.branch_id)
        assert branch is not None
        return self._scores[branch.label]


def _make_execution_port():
    from tests.test_phase16_rd_agent import _DeterministicExecutionPort

    return _DeterministicExecutionPort()


def _hypothesis_specs() -> list[HypothesisSpec]:
    return [
        HypothesisSpec(
            label="primary",
            approach_category=ApproachCategory.FEATURE_ENGINEERING,
            target_challenge="test",
            rationale="primary hypothesis",
        ),
        HypothesisSpec(
            label="alt-a",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="test",
            rationale="alt hypothesis",
        ),
    ]


def _stage_inputs() -> dict[StageKey, dict[str, object]]:
    return {
        StageKey.FRAMING: {"summary": "Framing.", "artifact_ids": ["a1"]},
        StageKey.BUILD: {"summary": "Build.", "artifact_ids": ["a2"]},
        StageKey.VERIFY: {"summary": "Verify.", "artifact_ids": ["a3"]},
        StageKey.SYNTHESIZE: {"summary": "Synth.", "artifact_ids": ["a4"], "recommendation": "stop"},
    }


def _base_rd_agent_kwargs(tmp_path: Path) -> dict[str, object]:
    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(state_store=state_store, execution_port=_make_execution_port())
    return {
        "title": "Phase 31 integration test",
        "task_summary": "Test graceful degradation.",
        "scenario_label": "research",
        "initial_branch_label": "primary",
        "dispatcher": lambda payload: payload,
        "execution_mode": ExecutionMode.UNATTENDED,
        "max_stage_iterations": 1,
        "hypothesis_specs": _hypothesis_specs(),
        "stage_inputs": _stage_inputs(),
        "state_store": state_store,
        "run_service": run_service,
        "recovery_service": RecoveryService(state_store),
        "transition_service": StageTransitionService(state_store),
    }


def _build_share_service(
    tmp_path: Path,
    *,
    embedding_port=None,
) -> tuple[ArtifactStateStore, BranchShareService, str, list[str]]:
    state_store = ArtifactStateStore(tmp_path / "share-state")
    run_service = RunBoardService(state_store=state_store, execution_port=_make_execution_port())
    start_response = run_service.start_run(
        RunStartRequest(
            title="share run",
            task_summary="share run",
            scenario_label="research",
            initial_branch_label="primary",
            execution_mode=ExecutionMode.UNATTENDED,
            branch_hypotheses=["primary", "peer-a", "peer-b"],
        )
    )
    run_id = start_response.run.run_id
    workspace_manager = BranchWorkspaceManager(getattr(state_store, "_root", ".state"))
    lifecycle_service = BranchLifecycleService(
        state_store=state_store,
        workspace_manager=workspace_manager,
        run_board_service=run_service,
    )
    peer_a = lifecycle_service.fork_branch(
        BranchForkRequest(
            run_id=run_id,
            source_branch_id=start_response.branch.branch_id,
            label="peer-a",
            rationale="peer a",
        )
    )
    peer_b = lifecycle_service.fork_branch(
        BranchForkRequest(
            run_id=run_id,
            source_branch_id=start_response.branch.branch_id,
            label="peer-b",
            rationale="peer b",
        )
    )
    branch_ids = [start_response.branch.branch_id, peer_a.branch.branch_id, peer_b.branch.branch_id]
    dag_service = MagicMock()
    dag_service.list_nodes.return_value = [
        MagicMock(branch_id=branch_ids[0], depth=1),
        MagicMock(branch_id=branch_ids[1], depth=1),
        MagicMock(branch_id=branch_ids[2], depth=1),
    ]
    service = BranchShareService(
        state_store,
        _NoopMemoryService(),
        embedding_port=embedding_port,
        dag_service=dag_service,
    )
    return state_store, service, run_id, branch_ids


def test_rd_agent_with_missing_holdout_port_does_not_raise(tmp_path):
    from rd_agent.entry.rd_agent import rd_agent

    result = rd_agent(**_base_rd_agent_kwargs(tmp_path))

    assert result["structuredContent"]["run"]["run_id"]


def test_rd_agent_without_holdout_port_injects_no_holdout_service(tmp_path, monkeypatch):
    from rd_agent.entry.rd_agent import rd_agent

    captured = {}
    original_init = MultiBranchService.__init__

    def _capture_init(self, **kwargs):
        captured.update(kwargs)
        return original_init(self, **kwargs)

    monkeypatch.setattr(MultiBranchService, "__init__", _capture_init)

    rd_agent(**_base_rd_agent_kwargs(tmp_path))

    assert captured["holdout_validation_service"] is None


def test_rd_agent_without_holdout_port_sets_finalization_skipped_true(tmp_path):
    from rd_agent.entry.rd_agent import rd_agent

    result = rd_agent(**_base_rd_agent_kwargs(tmp_path))

    assert result["structuredContent"]["finalization_skipped"] is True


def test_rd_agent_with_holdout_port_sets_finalization_skipped_false(tmp_path, monkeypatch):
    from rd_agent.entry.rd_agent import rd_agent

    kwargs = _base_rd_agent_kwargs(tmp_path)
    state_store = kwargs["state_store"]
    original_write = state_store.write_run_snapshot

    def _force_single_round(run_snapshot):
        return original_write(run_snapshot.model_copy(update={"max_rounds": 1}))

    monkeypatch.setattr(state_store, "write_run_snapshot", _force_single_round)
    kwargs["holdout_evaluation_port"] = StubEvaluationPort()
    kwargs["holdout_split_port"] = StubHoldoutSplitPort()

    result = rd_agent(**kwargs)

    assert result["structuredContent"]["finalization_skipped"] is False
    assert result["structuredContent"]["finalization_guidance"] is not None
    assert "exploring round 1/1" in result["structuredContent"]["finalization_guidance"]["current_state"]
    assert result["structuredContent"]["board"]["mode"] == "finalized"


def test_explore_round_request_accepts_branch_list():
    request = ExploreRoundRequest.model_validate(
        {
            "run_id": "run-1",
            "hypotheses": ["h1"],
            "branch_list": ["b1", "b2"],
        }
    )

    assert request.branch_list == ["b1", "b2"]


def test_explore_round_request_defaults_branch_list_to_empty():
    request = ExploreRoundRequest.model_validate({"run_id": "run-1", "hypotheses": ["h1"]})

    assert request.branch_list == []


def test_compute_sharing_candidates_uses_agent_branch_list_when_embedding_unavailable(tmp_path):
    _state_store, service, run_id, branch_ids = _build_share_service(
        tmp_path,
        embedding_port=_ExplodingEmbeddingPort(),
    )

    candidates = service.compute_sharing_candidates(
        run_id=run_id,
        target_branch_id=branch_ids[0],
        current_round=1,
        budget_ratio=0.5,
        agent_branch_list=[branch_ids[2]],
    )

    assert candidates == [branch_ids[2]]


def test_compute_sharing_candidates_merges_kernel_and_agent_lists_with_dedup(tmp_path):
    vectors = {
        "primary": [1.0, 0.0, 0.0],
        "peer-a": [0.9, 0.1, 0.0],
        "peer-b": [0.8, 0.2, 0.0],
    }
    _state_store, service, run_id, branch_ids = _build_share_service(
        tmp_path,
        embedding_port=_DeterministicEmbeddingPort(vectors),
    )

    candidates = service.compute_sharing_candidates(
        run_id=run_id,
        target_branch_id=branch_ids[0],
        current_round=1,
        budget_ratio=1.0,
        agent_branch_list=[branch_ids[1], branch_ids[2], branch_ids[1]],
    )

    assert set(candidates) == {branch_ids[1], branch_ids[2]}
    assert len(candidates) == 2


def test_compute_sharing_candidates_excludes_target_branch_from_agent_list(tmp_path):
    _state_store, service, run_id, branch_ids = _build_share_service(
        tmp_path,
        embedding_port=_ExplodingEmbeddingPort(),
    )

    candidates = service.compute_sharing_candidates(
        run_id=run_id,
        target_branch_id=branch_ids[0],
        current_round=1,
        budget_ratio=0.5,
        agent_branch_list=[branch_ids[0], branch_ids[2]],
    )

    assert candidates == [branch_ids[2]]


def test_build_finalization_guidance_includes_round_progress_text():
    submission = FinalSubmissionSnapshot.model_validate(
        {
            "submission_id": "submission-1",
            "run_id": "run-1",
            "winner_node_id": "node-1",
            "winner_branch_id": "branch-1",
            "holdout_mean": 0.9,
            "holdout_std": 0.01,
            "ranked_candidates": [],
        }
    )

    guidance = build_finalization_guidance(
        submission=submission,
        current_round=3,
        max_rounds=20,
    )

    assert "exploring round 3/20" in guidance.current_state


def test_build_finalization_guidance_regression_without_round_progress():
    submission = FinalSubmissionSnapshot.model_validate(
        {
            "submission_id": "submission-1",
            "run_id": "run-1",
            "winner_node_id": "node-1",
            "winner_branch_id": "branch-1",
            "holdout_mean": 0.9,
            "holdout_std": 0.01,
            "ranked_candidates": [],
        }
    )

    guidance = build_finalization_guidance(submission=submission)

    assert "finalization complete" in guidance.current_state.lower()
