from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import (
    ApproachCategory,
    ComponentClass,
    EdgeType,
    ExplorationMode,
    FinalSubmissionSnapshot,
    HypothesisSpec,
)
from v3.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import BranchMergeRequest, ExploreRoundRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_lifecycle_service import BranchLifecycleService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.convergence_service import ConvergenceService
from v3.orchestration.dag_service import DAGService
from v3.orchestration.holdout_validation_service import HoldoutValidationService
from v3.orchestration.multi_branch_service import MultiBranchService
from v3.orchestration.operator_guidance import build_finalization_guidance, render_operator_guidance_text
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.selection_service import SelectionService
from v3.ports.holdout_port import StubHoldoutSplitPort


def _stage() -> StageSnapshot:
    return StageSnapshot(
        stage_key=StageKey.BUILD,
        status=StageStatus.COMPLETED,
        summary="Build complete.",
        next_stage_key=StageKey.VERIFY,
    )


def _branch(branch_id: str, quality: float) -> BranchSnapshot:
    return BranchSnapshot(
        branch_id=branch_id,
        run_id="run-phase28-integration",
        label=branch_id,
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.BUILD,
        stages=[_stage()],
        score=BranchScore(
            exploration_priority=quality,
            result_quality=quality,
            rationale=f"{branch_id} quality snapshot.",
        ),
        lineage=BranchLineage(source_summary=f"{branch_id} lineage."),
        artifact_ids=[],
    )


class _ScoreByBranchPort:
    def __init__(self, branch_scores: dict[str, float], state_store: ArtifactStateStore) -> None:
        self._branch_scores = branch_scores
        self._state_store = state_store

    def evaluate(self, *, candidate_node_id: str, fold) -> float:
        node = self._state_store.load_dag_node(candidate_node_id)
        if node is None:
            return 0.5
        return self._branch_scores.get(node.branch_id, 0.5)


class _LatestNodeParentSelector:
    def __init__(self, dag_service: DAGService) -> None:
        self._dag_service = dag_service

    def select_parents(self, *, run_id: str, branch_id: str):
        branch_nodes = [node for node in self._dag_service.list_nodes(run_id) if node.branch_id == branch_id]
        if not branch_nodes:
            return SimpleNamespace(parent_node_ids=[])
        latest = max(branch_nodes, key=lambda node: node.depth)
        return SimpleNamespace(parent_node_ids=[latest.node_id])


class _CapturingMerger:
    def __init__(self, *, holdout_score: float = 0.95) -> None:
        self.holdout_score = holdout_score

    def merge(self, traces: list[dict], task_summary: str, scenario_name: str):
        from v3.algorithms.merge import MergeDesign

        return MergeDesign(
            summary=f"Synthesized for {scenario_name}",
            operation="create",
            source_branch_ids=tuple(trace["branch_id"] for trace in traces),
            component_analysis="captured-components",
            holdout_score=self.holdout_score,
        )


def _build_phase28_context(tmp_path: Path):
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    workspace_manager = BranchWorkspaceManager(tmp_path / "state")
    run_board_service = RunBoardService(state_store)
    branches = [
        _branch("brA", 0.90),
        _branch("brB", 0.80),
        _branch("brC", 0.65),
    ]
    for branch in branches:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-phase28-integration",
            title="Phase 28 integration",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            exploration_mode=ExplorationMode.EXPLORATION,
            branch_ids=[branch.branch_id for branch in branches],
            primary_branch_id="brA",
            highlighted_artifact_ids=[],
            summary="Phase 28 integration summary.",
            current_round=0,
            max_rounds=2,
        )
    )
    branch_scores = {"brA": 0.92, "brB": 0.85, "brC": 0.70}
    holdout_service = HoldoutValidationService(
        state_store=state_store,
        dag_service=dag_service,
        split_port=StubHoldoutSplitPort(k=5),
        evaluation_port=_ScoreByBranchPort(branch_scores, state_store),
    )
    merge_service = BranchMergeService(
        state_store=state_store,
        convergence_service=convergence_service,
        board_service=board_service,
        merger=_CapturingMerger(),
        dag_service=dag_service,
    )
    multi_branch_service = MultiBranchService(
        state_store=state_store,
        workspace_manager=workspace_manager,
        branch_lifecycle_service=BranchLifecycleService(
            state_store=state_store,
            workspace_manager=workspace_manager,
            run_board_service=run_board_service,
        ),
        branch_board_service=board_service,
        selection_service=SelectionService(state_store=state_store),
        branch_merge_service=merge_service,
        dispatcher=lambda payload: payload,
        dag_service=dag_service,
        select_parents_service=_LatestNodeParentSelector(dag_service),
        holdout_validation_service=holdout_service,
    )
    hypothesis_specs = [
        HypothesisSpec(
            label="brA",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="integration",
            rationale="branch A hypothesis",
        ),
        HypothesisSpec(
            label="brB",
            approach_category=ApproachCategory.FEATURE_ENGINEERING,
            target_challenge="integration",
            rationale="branch B hypothesis",
        ),
        HypothesisSpec(
            label="brC",
            approach_category=ApproachCategory.DATA_AUGMENTATION,
            target_challenge="integration",
            rationale="branch C hypothesis",
        ),
    ]
    return state_store, dag_service, merge_service, multi_branch_service, hypothesis_specs


def _run_to_finalization(tmp_path: Path) -> tuple[ArtifactStateStore, DAGService, MultiBranchService, FinalSubmissionSnapshot]:
    state_store, dag_service, _merge_service, multi_branch_service, hypothesis_specs = _build_phase28_context(tmp_path)
    multi_branch_service.run_exploration_round(
        ExploreRoundRequest(
            run_id="run-phase28-integration",
            hypotheses=["brA", "brB", "brC"],
            hypothesis_specs=hypothesis_specs,
            auto_prune=False,
        )
    )
    result = multi_branch_service.run_exploration_round(
        ExploreRoundRequest(
            run_id="run-phase28-integration",
            hypotheses=["brA", "brB", "brC"],
            hypothesis_specs=hypothesis_specs,
            auto_prune=False,
        )
    )
    assert result.finalization_submission is not None
    return state_store, dag_service, multi_branch_service, result.finalization_submission


def test_full_lifecycle_explore_to_finalize(tmp_path: Path) -> None:
    _state_store, _dag_service, _multi_branch_service, submission = _run_to_finalization(tmp_path)

    assert isinstance(submission, FinalSubmissionSnapshot)
    assert submission.winner_branch_id == "brA"
    assert submission.ranked_candidates
    assert submission.ranked_candidates[0].holdout_mean >= submission.ranked_candidates[-1].holdout_mean


def test_finalization_persists_holdout_metrics(tmp_path: Path) -> None:
    state_store, _dag_service, _multi_branch_service, submission = _run_to_finalization(tmp_path)

    winner_node = state_store.load_dag_node(submission.winner_node_id)

    assert winner_node is not None
    assert winner_node.node_metrics.holdout_mean > 0.0
    assert winner_node.node_metrics.holdout_std == 0.0


def test_finalization_ancestry_chain(tmp_path: Path) -> None:
    state_store, _dag_service, _multi_branch_service, submission = _run_to_finalization(tmp_path)

    winner_node = state_store.load_dag_node(submission.winner_node_id)

    assert winner_node is not None
    assert winner_node.parent_node_ids
    assert set(winner_node.parent_node_ids).issubset(set(submission.ancestry_chain))


def test_finalization_with_merged_nodes(tmp_path: Path) -> None:
    state_store, dag_service, merge_service, _multi_branch_service, _hypothesis_specs = _build_phase28_context(tmp_path)
    initial_nodes = []
    for branch_id in ("brA", "brB", "brC"):
        initial_nodes.append(dag_service.create_node(run_id="run-phase28-integration", branch_id=branch_id))

    merge_service.merge_with_complementarity(
        BranchMergeRequest(run_id="run-phase28-integration", minimum_quality=0.6),
        {
            "brA": {"model": 0.9},
            "brB": {"ensemble": 0.9},
            "brC": {"workflow": 0.8},
        },
    )
    merged_nodes = [
        node
        for node in dag_service.list_nodes("run-phase28-integration")
        if node.node_id not in {original.node_id for original in initial_nodes}
    ]
    assert merged_nodes

    holdout_service = HoldoutValidationService(
        state_store=state_store,
        dag_service=dag_service,
        split_port=StubHoldoutSplitPort(k=5),
        evaluation_port=_ScoreByBranchPort({"brA": 0.95, "brB": 0.80, "brC": 0.70}, state_store),
    )
    submission = holdout_service.finalize(run_id="run-phase28-integration")

    assert any(entry.node_id in {node.node_id for node in merged_nodes} for entry in submission.ranked_candidates)


def test_early_finalization(tmp_path: Path) -> None:
    state_store, _dag_service, _merge_service, multi_branch_service, hypothesis_specs = _build_phase28_context(
        tmp_path
    )
    multi_branch_service.run_exploration_round(
        ExploreRoundRequest(
            run_id="run-phase28-integration",
            hypotheses=["brA", "brB", "brC"],
            hypothesis_specs=hypothesis_specs,
            auto_prune=False,
        )
    )

    submission = multi_branch_service.finalize_early(run_id="run-phase28-integration")

    assert isinstance(submission, FinalSubmissionSnapshot)
    assert state_store.load_final_submission("run-phase28-integration") == submission


def test_operator_guidance_for_finalization(tmp_path: Path) -> None:
    _state_store, _dag_service, _multi_branch_service, submission = _run_to_finalization(tmp_path)

    guidance = build_finalization_guidance(submission=submission)
    rendered = render_operator_guidance_text(guidance)

    assert "finalization complete" in guidance.current_state.lower()
    assert submission.winner_node_id in guidance.current_state
    assert submission.winner_node_id in rendered
    assert "holdout_mean" in rendered


def test_final_submission_persistence(tmp_path: Path) -> None:
    state_store, _dag_service, _multi_branch_service, submission = _run_to_finalization(tmp_path)

    loaded = state_store.load_final_submission("run-phase28-integration")

    assert loaded == submission
    assert loaded is not None
    assert loaded.winner_node_id == submission.winner_node_id
    assert len(loaded.ranked_candidates) == len(submission.ranked_candidates)


# ------------------------------------------------------------------
# Regression tests for Codex-found bugs
# ------------------------------------------------------------------


class _MinimalMergeService:
    """Merge service with only merge() and fallback() — no merge_with_complementarity."""

    def __init__(self, board_service: BranchBoardService) -> None:
        self._board_service = board_service

    def merge(self, request: BranchMergeRequest):
        from v3.contracts.tool_io import BranchMergeResult, MergeOutcomeSnapshot

        board = self._board_service.get_board(request.run_id)
        return BranchMergeResult(
            outcome=MergeOutcomeSnapshot(
                outcome_id="minimal-merge",
                run_id=request.run_id,
                summary="Minimal merge declined.",
                rationale="Minimal service.",
                failure_reason="not_implemented",
                shortlist=[],
            ),
            board=board,
        )

    def fallback(self, request):
        raise ValueError("Minimal service has no fallback.")


def test_convergence_with_minimal_merge_service(tmp_path: Path) -> None:
    """Regression: merge service without merge_with_complementarity must not crash."""
    from v3.contracts.tool_io import ConvergeRoundRequest

    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    board_service = BranchBoardService(state_store)
    workspace_manager = BranchWorkspaceManager(tmp_path / "state")
    run_board_service = RunBoardService(state_store)

    branches = [_branch("brX", 0.90), _branch("brY", 0.80)]
    for branch in branches:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-minimal",
            title="Minimal merge test",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            exploration_mode=ExplorationMode.EXPLORATION,
            branch_ids=["brX", "brY"],
            primary_branch_id="brX",
            highlighted_artifact_ids=[],
            summary="Minimal merge test.",
            current_round=0,
            max_rounds=2,
        )
    )
    for bid in ("brX", "brY"):
        dag_service.create_node(run_id="run-minimal", branch_id=bid)

    # Use a merge service that does NOT have merge_with_complementarity
    service = MultiBranchService(
        state_store=state_store,
        workspace_manager=workspace_manager,
        branch_lifecycle_service=BranchLifecycleService(
            state_store=state_store,
            workspace_manager=workspace_manager,
            run_board_service=run_board_service,
        ),
        branch_board_service=board_service,
        selection_service=SelectionService(state_store=state_store),
        branch_merge_service=_MinimalMergeService(board_service),
        dispatcher=lambda payload: payload,
        dag_service=dag_service,
        branch_share_service=SimpleNamespace(find_sharing_candidates=lambda **_kw: []),
    )

    # Must not raise AttributeError
    result = service.run_convergence_round(ConvergeRoundRequest(run_id="run-minimal"))
    assert result.selected_branch_id in ("brX", "brY")


def test_selection_service_rejects_unknown_adapter_branch_id(tmp_path: Path) -> None:
    """Regression: adapter returning non-existent branch id raises ValueError, not StopIteration."""
    from v3.contracts.recovery import RecoveryAssessment, RecoveryDisposition
    from v3.orchestration.selection_service import SelectionService

    state_store = ArtifactStateStore(tmp_path / "state")
    branch = _branch("brReal", 0.90)
    state_store.write_branch_snapshot(branch)
    state_store.write_recovery_assessment(
        RecoveryAssessment(
            run_id="run-sel",
            branch_id="brReal",
            stage_key=StageKey.BUILD,
            recovery_assessment=RecoveryDisposition.REUSE,
            reusable_artifact_ids=["a1"],
            replay_artifact_ids=[],
            invalid_reasons=[],
            recommended_next_step="continue",
        )
    )
    state_store.write_hypothesis_spec(
        "brReal",
        HypothesisSpec(
            label="brReal",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="test",
            rationale="test",
            component_classes=(ComponentClass.MODEL,),
        ),
    )
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-sel",
            title="Selection test",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            exploration_mode=ExplorationMode.EXPLORATION,
            branch_ids=["brReal"],
            primary_branch_id="brReal",
            highlighted_artifact_ids=[],
            summary="Selection test.",
            current_round=0,
            max_rounds=2,
        )
    )

    class _BadAdapter:
        def select_next_branch(self, candidates):
            return "nonexistent-branch-id"

    service = SelectionService(state_store=state_store, adapter=_BadAdapter())

    # Must raise ValueError (not StopIteration)
    try:
        service.select_next_branch(run_id="run-sel")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "nonexistent-branch-id" in str(exc)
