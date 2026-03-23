from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import pytest

from v3.contracts.artifact import ArtifactKind, ArtifactLocator, ArtifactProvenance, ArtifactReuseLevel, ArtifactSnapshot
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import ApproachCategory, ExplorationMode, HypothesisSpec
from v3.contracts.run import ExecutionMode
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import BranchPruneResult, ExploreRoundRequest, RunStartRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_lifecycle_service import BranchLifecycleService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.branch_prune_service import BranchPruneService
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.convergence_service import ConvergenceService
from v3.orchestration.dag_service import DAGService
from v3.orchestration.multi_branch_service import MultiBranchService
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.select_parents_service import SelectParentsService
from v3.orchestration.selection_service import SelectionService
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.ports.execution import ExecutionPort, ExecutionStartResult


@dataclass
class _DeterministicExecutionPort(ExecutionPort):
    def start_run(self, request: RunStartRequest) -> ExecutionStartResult:
        artifact = ArtifactSnapshot(
            artifact_id="artifact-framing-001",
            branch_id="branch-001",
            stage_key=StageKey.FRAMING,
            kind=ArtifactKind.PLAN,
            title=request.title,
            summary=request.task_summary,
            locator=ArtifactLocator(
                uri="memory://artifacts/artifact-framing-001.json",
                media_type="application/json",
                size_bytes=128,
            ),
            provenance=ArtifactProvenance(
                created_by="test",
                source_branch_ids=["branch-001"],
                captured_at="2026-03-20T10:00:00Z",
            ),
            reuse_level=ArtifactReuseLevel.REFERENCE,
            tags=["framing"],
        )
        stage = StageSnapshot(
            stage_key=StageKey.FRAMING,
            stage_iteration=1,
            status=StageStatus.IN_PROGRESS,
            summary=f"Framing started for: {request.task_summary}",
            artifact_ids=[artifact.artifact_id],
            next_stage_key=StageKey.BUILD,
        )
        branch = BranchSnapshot(
            branch_id="branch-001",
            run_id="run-001",
            label=request.initial_branch_label or "primary",
            status=BranchStatus.ACTIVE,
            current_stage_key=StageKey.FRAMING,
            stages=[stage],
            score=BranchScore(
                exploration_priority=1.0,
                result_quality=0.0,
                rationale="Primary branch remains active.",
            ),
            lineage=BranchLineage(source_summary="Created in test state."),
            artifact_ids=[artifact.artifact_id],
        )
        return ExecutionStartResult(branch=branch, stage=stage, artifacts=[artifact])


class _SpyPruneService:
    def __init__(self, board_service: BranchBoardService) -> None:
        self._board_service = board_service
        self.calls: list[str] = []

    def prune(self, request) -> BranchPruneResult:
        self.calls.append(request.run_id)
        board = self._board_service.get_board(request.run_id)
        return BranchPruneResult(
            run_id=request.run_id,
            active_branch_ids=[card.branch_id for card in board.active_cards],
            pruned_branch_ids=["simulated-prune"],
            decision_ids=[],
            board=board,
        )


def _build_service(
    tmp_path: Path,
    *,
    current_round: int = 0,
    with_dag: bool = False,
    prune_mode: str | None = None,
    with_select_parents: bool = False,
    dispatcher=None,
) -> tuple[ArtifactStateStore, MultiBranchService, list[dict[str, str]], object | None]:
    dispatches: list[dict[str, str]] = []

    def _dispatcher(payload):
        dispatches.append(payload)
        return payload

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(state_store=state_store, execution_port=_DeterministicExecutionPort())
    publication = run_service.start_run(
        RunStartRequest(
            title="Phase 26 task",
            task_summary="Drive integrated exploration.",
            scenario_label="research",
            initial_branch_label="primary",
            execution_mode=ExecutionMode.UNATTENDED,
            exploration_mode=ExplorationMode.EXPLORATION,
        )
    )
    state_store.write_run_snapshot(
        publication.run.model_copy(update={"current_round": current_round, "exploration_mode": ExplorationMode.EXPLORATION})
    )
    workspace_manager = BranchWorkspaceManager(tmp_path / "state")
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    dag_service = DAGService(state_store) if with_dag else None
    if prune_mode == "spy":
        prune_service = _SpyPruneService(board_service)
    elif prune_mode == "real":
        prune_service = BranchPruneService(state_store=state_store, board_service=board_service)
    else:
        prune_service = None
    select_parents_service = (
        SelectParentsService(state_store, dag_service)
        if with_select_parents and dag_service is not None
        else None
    )
    service = MultiBranchService(
        state_store=state_store,
        workspace_manager=workspace_manager,
        branch_lifecycle_service=BranchLifecycleService(
            state_store=state_store,
            workspace_manager=workspace_manager,
            run_board_service=run_service,
        ),
        branch_board_service=board_service,
        selection_service=SelectionService(state_store=state_store),
        branch_merge_service=BranchMergeService(
            state_store=state_store,
            convergence_service=convergence_service,
            board_service=board_service,
        ),
        dispatcher=dispatcher or _dispatcher,
        dag_service=dag_service,
        prune_service=prune_service,
        select_parents_service=select_parents_service,
    )
    return state_store, service, dispatches, prune_service


def test_run_exploration_round_creates_dag_nodes_increments_round_and_prunes(tmp_path: Path) -> None:
    state_store, service, dispatches, prune_service = _build_service(
        tmp_path,
        current_round=0,
        with_dag=True,
        prune_mode="spy",
    )
    specs = [
        HypothesisSpec(
            label="primary",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="baseline",
            rationale="Keep the seed branch.",
        ),
        HypothesisSpec(
            label="alt-a",
            approach_category=ApproachCategory.FEATURE_ENGINEERING,
            target_challenge="representation",
            rationale="Explore feature-focused variant.",
        ),
        HypothesisSpec(
            label="alt-b",
            approach_category=ApproachCategory.ENSEMBLE,
            target_challenge="variance",
            rationale="Explore ensemble variant.",
        ),
    ]

    result = service.run_exploration_round(
        ExploreRoundRequest(run_id="run-001", hypothesis_specs=specs)
    )

    run = state_store.load_run_snapshot("run-001")
    nodes = state_store.list_dag_nodes("run-001")

    assert len(dispatches) == 3
    assert [payload["label"] for payload in dispatches] == ["primary", "alt-a", "alt-b"]
    assert len(result.dag_node_ids) == 3
    assert result.pruned_branch_ids == ["simulated-prune"]
    assert result.round_diversity_score == pytest.approx(math.log2(3), abs=1e-6)
    assert isinstance(prune_service, _SpyPruneService)
    assert prune_service.calls == ["run-001"]
    assert run is not None
    assert run.current_round == 1
    assert len(nodes) == 3
    for node_id, branch_id in zip(result.dag_node_ids, result.dispatched_branch_ids, strict=True):
        node = state_store.load_dag_node(node_id)
        assert node is not None
        assert node.branch_id == branch_id
        assert node.node_metrics.diversity_score == pytest.approx(math.log2(3), abs=1e-6)
        assert node.node_metrics.validation_score == 0.0
        assert node.node_metrics.generalization_gap == 0.0
        assert node.node_metrics.overfitting_risk == 0.0


def test_run_exploration_round_rejects_duplicate_first_layer_categories(tmp_path: Path) -> None:
    state_store, service, dispatches, _ = _build_service(tmp_path, with_dag=True)
    specs = [
        HypothesisSpec(
            label="primary",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="baseline",
            rationale="Keep the seed branch.",
        ),
        HypothesisSpec(
            label="alt-a",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="duplicate",
            rationale="This should be rejected.",
        ),
    ]

    with pytest.raises(ValueError, match="Duplicate approach_category"):
        service.run_exploration_round(ExploreRoundRequest(run_id="run-001", hypothesis_specs=specs))

    run = state_store.load_run_snapshot("run-001")

    assert dispatches == []
    assert run is not None
    assert run.branch_ids == ["branch-001"]
    assert run.current_round == 0
    assert state_store.list_dag_nodes("run-001") == []


def test_run_exploration_round_falls_back_to_string_hypotheses_and_optional_services(tmp_path: Path) -> None:
    state_store, service, dispatches, _ = _build_service(tmp_path)

    result = service.run_exploration_round(
        ExploreRoundRequest(
            run_id="run-001",
            hypotheses=["primary", "alt-a"],
            auto_prune=False,
        )
    )

    run = state_store.load_run_snapshot("run-001")

    assert len(dispatches) == 2
    assert [payload["label"] for payload in dispatches] == ["primary", "alt-a"]
    assert result.dag_node_ids == []
    assert result.pruned_branch_ids == []
    assert run is not None
    assert run.current_round == 1


def test_run_exploration_round_reports_unknown_round_diversity_without_specs(tmp_path: Path) -> None:
    state_store, service, _dispatches, _ = _build_service(tmp_path, with_dag=True)

    result = service.run_exploration_round(
        ExploreRoundRequest(run_id="run-001", hypotheses=["primary", "alt-a"])
    )

    nodes = state_store.list_dag_nodes("run-001")

    assert result.round_diversity_score is None
    assert len(nodes) == 2
    assert all(node.node_metrics.diversity_score == 0.0 for node in nodes)


def test_run_exploration_round_rejects_empty_hypothesis_input(tmp_path: Path) -> None:
    _state_store, service, _dispatches, _ = _build_service(tmp_path)

    with pytest.raises(ValueError, match="exploration round requires at least one hypothesis"):
        service.run_exploration_round(ExploreRoundRequest(run_id="run-001"))


def test_auto_prune_false_skips_present_prune_service(tmp_path: Path) -> None:
    state_store, service, dispatches, prune_service = _build_service(tmp_path, prune_mode="spy")

    result = service.run_exploration_round(
        ExploreRoundRequest(
            run_id="run-001",
            hypotheses=["primary", "alt-a"],
            auto_prune=False,
        )
    )

    run = state_store.load_run_snapshot("run-001")

    assert isinstance(prune_service, _SpyPruneService)
    assert prune_service.calls == []
    assert len(dispatches) == 2
    assert result.pruned_branch_ids == []
    assert run is not None
    assert run.current_round == 1


def test_run_exploration_round_creates_non_root_nodes_after_first_round(tmp_path: Path) -> None:
    state_store, service, _dispatches, _ = _build_service(
        tmp_path,
        with_dag=True,
        with_select_parents=True,
    )
    specs = [
        HypothesisSpec(
            label="primary",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="baseline",
            rationale="Keep the seed branch.",
        ),
        HypothesisSpec(
            label="alt-a",
            approach_category=ApproachCategory.FEATURE_ENGINEERING,
            target_challenge="representation",
            rationale="Explore feature-focused variant.",
        ),
    ]

    first = service.run_exploration_round(ExploreRoundRequest(run_id="run-001", hypothesis_specs=specs))
    second = service.run_exploration_round(ExploreRoundRequest(run_id="run-001", hypothesis_specs=specs))

    assert len(first.dag_node_ids) == 2
    later_nodes = [state_store.load_dag_node(node_id) for node_id in second.dag_node_ids]
    assert all(node is not None for node in later_nodes)
    assert all(node.parent_node_ids for node in later_nodes if node is not None)
    assert all(node.depth > 0 for node in later_nodes if node is not None)


def test_duplicate_categories_are_allowed_after_first_round(tmp_path: Path) -> None:
    _state_store, service, dispatches, _ = _build_service(tmp_path, current_round=1, with_dag=True)
    specs = [
        HypothesisSpec(
            label="primary",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="baseline",
            rationale="Keep the seed branch.",
        ),
        HypothesisSpec(
            label="alt-a",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="same-category-later",
            rationale="Later rounds may reuse the same category.",
        ),
    ]

    result = service.run_exploration_round(ExploreRoundRequest(run_id="run-001", hypothesis_specs=specs))

    assert len(result.dispatched_branch_ids) == 2
    assert len(dispatches) == 2


def test_rd_agent_accepts_hypothesis_specs_and_wires_phase26_services(tmp_path: Path) -> None:
    from v3.entry.rd_agent import rd_agent

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(state_store=state_store, execution_port=_DeterministicExecutionPort())
    specs = [
        HypothesisSpec(
            label="primary",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="baseline",
            rationale="Keep the seed branch.",
        ),
        HypothesisSpec(
            label="alt-a",
            approach_category=ApproachCategory.FEATURE_ENGINEERING,
            target_challenge="representation",
            rationale="Explore feature-focused variant.",
        ),
    ]

    result = rd_agent(
        title="Phase 26 task",
        task_summary="Drive integrated exploration.",
        scenario_label="research",
        initial_branch_label="primary",
        dispatcher=lambda payload: payload,
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=1,
        stage_inputs={
            StageKey.FRAMING: {"summary": "Framing complete.", "artifact_ids": ["artifact-framing-001"]},
            StageKey.BUILD: {"summary": "Build complete.", "artifact_ids": ["artifact-build-001"]},
            StageKey.VERIFY: {"summary": "Verify complete.", "artifact_ids": ["artifact-verify-001"]},
            StageKey.SYNTHESIZE: {"summary": "Synthesize complete.", "artifact_ids": ["artifact-synthesize-001"], "recommendation": "stop"},
        },
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
        hypothesis_specs=specs,
    )

    run = state_store.load_run_snapshot("run-001")
    nodes = state_store.list_dag_nodes("run-001")

    assert len(result["structuredContent"]["dispatches"]) == 2
    assert result["structuredContent"]["run"]["current_round"] == 1
    assert result["structuredContent"]["selected_branch_id"]
    assert result["structuredContent"]["merge_summary"]
    assert run is not None
    assert run.current_round == 1
    assert len(nodes) == 2


def test_rd_agent_rejects_mixed_hypothesis_inputs(tmp_path: Path) -> None:
    from v3.entry.rd_agent import rd_agent

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(state_store=state_store, execution_port=_DeterministicExecutionPort())

    with pytest.raises(ValueError, match="Provide either branch_hypotheses or hypothesis_specs, not both"):
        rd_agent(
            title="Phase 26 task",
            task_summary="Drive integrated exploration.",
            scenario_label="research",
            initial_branch_label="primary",
            branch_hypotheses=["legacy-a", "legacy-b"],
            hypothesis_specs=[
                HypothesisSpec(
                    label="structured-a",
                    approach_category=ApproachCategory.MODEL_ARCHITECTURE,
                    target_challenge="baseline",
                    rationale="structured",
                ),
                HypothesisSpec(
                    label="structured-b",
                    approach_category=ApproachCategory.FEATURE_ENGINEERING,
                    target_challenge="features",
                    rationale="structured",
                ),
            ],
            state_store=state_store,
            run_service=run_service,
            recovery_service=RecoveryService(state_store),
            transition_service=StageTransitionService(state_store),
            stage_inputs={},
        )


def test_rd_agent_legacy_string_hypotheses_remain_side_effect_neutral(tmp_path: Path) -> None:
    from v3.entry.rd_agent import rd_agent

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(state_store=state_store, execution_port=_DeterministicExecutionPort())

    result = rd_agent(
        title="Phase 26 task",
        task_summary="Legacy multi-branch exploration.",
        scenario_label="research",
        initial_branch_label="primary",
        branch_hypotheses=["primary", "alt-a"],
        dispatcher=lambda payload: payload,
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=1,
        stage_inputs={
            StageKey.FRAMING: {"summary": "Framing complete.", "artifact_ids": ["artifact-framing-001"]},
            StageKey.BUILD: {"summary": "Build complete.", "artifact_ids": ["artifact-build-001"]},
            StageKey.VERIFY: {"summary": "Verify complete.", "artifact_ids": ["artifact-verify-001"]},
            StageKey.SYNTHESIZE: {"summary": "Synthesize complete.", "artifact_ids": ["artifact-synthesize-001"], "recommendation": "stop"},
        },
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    assert len(result["structuredContent"]["dispatches"]) == 2
    assert "branch-001" in result["structuredContent"]["dispatches"]
    assert state_store.list_dag_nodes("run-001") == []
