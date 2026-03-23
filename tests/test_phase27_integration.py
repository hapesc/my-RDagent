from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from v3.algorithms.merge import MergeDesign
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import (
    ApproachCategory,
    EdgeType,
    ExplorationMode,
    HypothesisSpec,
    NodeMetrics,
)
from v3.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import BranchMergeRequest, BranchPruneRequest, ExploreRoundRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_lifecycle_service import BranchLifecycleService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.branch_prune_service import BranchPruneService
from v3.orchestration.branch_share_service import BranchShareService
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.convergence_service import ConvergenceService
from v3.orchestration.dag_service import DAGService
from v3.orchestration.multi_branch_service import MultiBranchService
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.selection_service import SelectionService


def _stage() -> StageSnapshot:
    return StageSnapshot(
        stage_key=StageKey.BUILD,
        status=StageStatus.COMPLETED,
        summary="Build complete.",
        next_stage_key=StageKey.VERIFY,
    )


def _branch(branch_id: str, label: str, quality: float) -> BranchSnapshot:
    return BranchSnapshot(
        branch_id=branch_id,
        run_id="run-phase27",
        label=label,
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.BUILD,
        stages=[_stage()],
        score=BranchScore(
            exploration_priority=quality,
            result_quality=quality,
            rationale=f"{label} quality snapshot.",
        ),
        lineage=BranchLineage(source_summary=f"{label} lineage."),
        artifact_ids=[],
    )


class _StaticEmbeddingPort:
    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._mapping[text] for text in texts]


class _CapturingMerger:
    def __init__(self, *, holdout_score: float | None = 0.95) -> None:
        self.holdout_score = holdout_score
        self.last_design: MergeDesign | None = None

    def merge(self, traces: list[dict], task_summary: str, scenario_name: str) -> MergeDesign:
        self.last_design = MergeDesign(
            summary=f"Synthesized for {scenario_name}",
            operation="create",
            source_branch_ids=tuple(trace["branch_id"] for trace in traces),
            component_analysis="captured-components",
            holdout_score=self.holdout_score,
        )
        return self.last_design


def _build_phase27_context(tmp_path: Path, *, current_round: int = 1, holdout_score: float | None = 0.95):
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    workspace_manager = BranchWorkspaceManager(tmp_path / "state")
    run_board_service = RunBoardService(state_store)
    branches = [
        _branch("branch-primary", "primary", 0.92),
        _branch("branch-peer", "peer", 0.15),
        _branch("branch-novel", "novel", 0.22),
    ]
    for branch in branches:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-phase27",
            title="Phase 27 integration",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            exploration_mode=ExplorationMode.EXPLORATION,
            branch_ids=[branch.branch_id for branch in branches],
            primary_branch_id=branches[0].branch_id,
            highlighted_artifact_ids=[],
            summary="Phase 27 integration summary.",
            current_round=current_round,
            max_rounds=4,
        )
    )
    component_specs = {
        "branch-primary": ("model",),
        "branch-peer": ("model",),
        "branch-novel": ("workflow",),
    }
    for branch in branches:
        state_store.write_hypothesis_spec(
            branch.branch_id,
            HypothesisSpec(
                label=branch.label,
                approach_category=ApproachCategory.MODEL_ARCHITECTURE,
                target_challenge="integration",
                rationale="phase27 integration spec",
                component_classes=component_specs[branch.branch_id],
            ),
        )
    dag_service.create_node(
        run_id="run-phase27",
        branch_id="branch-primary",
        node_metrics=NodeMetrics(validation_score=0.92, complementarity_score=0.15, diversity_score=0.20),
    )
    dag_service.create_node(
        run_id="run-phase27",
        branch_id="branch-peer",
        node_metrics=NodeMetrics(validation_score=0.15, complementarity_score=0.18, diversity_score=0.25),
    )
    dag_service.create_node(
        run_id="run-phase27",
        branch_id="branch-novel",
        node_metrics=NodeMetrics(validation_score=0.22, complementarity_score=0.95, diversity_score=0.90),
    )
    merger = _CapturingMerger(holdout_score=holdout_score)
    merge_service = BranchMergeService(
        state_store=state_store,
        convergence_service=convergence_service,
        board_service=board_service,
        merger=merger,
        dag_service=dag_service,
    )
    share_service = BranchShareService(
        state_store=state_store,
        memory_service=MagicMock(),
        dag_service=dag_service,
        embedding_port=_StaticEmbeddingPort(
            {
                "primary": [1.0, 0.0],
                "peer": [0.95, 0.05],
                "novel": [0.0, 1.0],
            }
        ),
    )
    dispatches: list[dict[str, object]] = []
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
        dispatcher=lambda payload: dispatches.append(payload),
        dag_service=dag_service,
        branch_share_service=share_service,
    )
    prune_service = BranchPruneService(
        state_store=state_store,
        board_service=board_service,
        dag_service=dag_service,
    )
    return state_store, dag_service, share_service, prune_service, merge_service, multi_branch_service, merger, dispatches


class TestSharingIntegration:
    def test_full_sharing_round_creates_shared_edges(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        state_store, dag_service, _share_service, _prune_service, _merge_service, multi_branch_service, _merger, dispatches = _build_phase27_context(
            tmp_path,
            current_round=1,
        )
        monkeypatch.setattr(
            "v3.algorithms.interaction_kernel.random.choices",
            lambda population, *, weights=None, k=1: [population[0]],
        )

        result = multi_branch_service.run_exploration_round(
            ExploreRoundRequest(
                run_id="run-phase27",
                hypotheses=["primary", "peer", "novel"],
                auto_prune=False,
            )
        )

        decisions = state_store.list_branch_decisions("run-phase27")
        edges = state_store.list_dag_edges("run-phase27")

        assert result.sharing_candidate_ids
        assert all("sharing_candidate_ids" in payload for payload in dispatches)
        assert any(decision.kind.value == "share" for decision in decisions)
        assert any(edge.edge_type is EdgeType.SHARED for edge in edges)

    def test_round_zero_guard_keeps_sharing_candidates_empty(self, tmp_path: Path) -> None:
        _state_store, _dag_service, _share_service, _prune_service, _merge_service, multi_branch_service, _merger, dispatches = _build_phase27_context(
            tmp_path,
            current_round=0,
        )

        result = multi_branch_service.run_exploration_round(
            ExploreRoundRequest(
                run_id="run-phase27",
                hypotheses=["primary", "peer", "novel"],
                auto_prune=False,
            )
        )

        assert result.sharing_candidate_ids == []
        assert all("sharing_candidate_ids" not in payload for payload in dispatches)


class TestPruningIntegration:
    def test_pruning_signal4_preserves_unique_component_branch(self, tmp_path: Path) -> None:
        _state_store, _dag_service, _share_service, prune_service, _merge_service, _multi_branch_service, _merger, _dispatches = _build_phase27_context(
            tmp_path,
            current_round=1,
        )

        result = prune_service.prune(BranchPruneRequest(run_id="run-phase27", relative_threshold=0.5))

        assert "branch-peer" in result.pruned_branch_ids
        assert "branch-novel" not in result.pruned_branch_ids


class TestMergeIntegration:
    def test_complementary_merge_creates_merged_edges_and_component_analysis(self, tmp_path: Path) -> None:
        _state_store, dag_service, _share_service, prune_service, merge_service, _multi_branch_service, merger, _dispatches = _build_phase27_context(
            tmp_path,
            current_round=1,
        )
        prune_service.prune(BranchPruneRequest(run_id="run-phase27", relative_threshold=0.5))
        branch_component_scores, _classes = dag_service.collect_branch_component_scores("run-phase27", merge_service._state_store)

        result = merge_service.merge_with_complementarity(
            BranchMergeRequest(run_id="run-phase27", minimum_quality=0.2),
            branch_component_scores,
        )

        edges = merge_service._state_store.list_dag_edges("run-phase27")

        assert result.outcome.merged_branch_id == "branch-primary"
        assert result.outcome.source_branch_ids == ["branch-primary", "branch-novel"]
        assert merger.last_design is not None
        assert merger.last_design.component_analysis == "captured-components"
        assert any(edge.edge_type is EdgeType.MERGED for edge in edges)

    def test_holdout_gate_rejects_weak_merged_candidate(self, tmp_path: Path) -> None:
        _state_store, dag_service, _share_service, prune_service, merge_service, _multi_branch_service, _merger, _dispatches = _build_phase27_context(
            tmp_path,
            current_round=1,
            holdout_score=0.10,
        )
        prune_service.prune(BranchPruneRequest(run_id="run-phase27", relative_threshold=0.5))
        branch_component_scores, _classes = dag_service.collect_branch_component_scores("run-phase27", merge_service._state_store)

        result = merge_service.merge_with_complementarity(
            BranchMergeRequest(run_id="run-phase27", minimum_quality=0.2),
            branch_component_scores,
        )

        assert result.outcome.failure_reason == "holdout_validation_failed"


class TestFullLifecycleIntegration:
    def test_full_lifecycle_sharing_prune_and_merge(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        state_store, dag_service, _share_service, prune_service, merge_service, multi_branch_service, _merger, _dispatches = _build_phase27_context(
            tmp_path,
            current_round=1,
        )
        monkeypatch.setattr(
            "v3.algorithms.interaction_kernel.random.choices",
            lambda population, *, weights=None, k=1: [population[0]],
        )

        explore_result = multi_branch_service.run_exploration_round(
            ExploreRoundRequest(
                run_id="run-phase27",
                hypotheses=["primary", "peer", "novel"],
                auto_prune=False,
            )
        )
        prune_result = prune_service.prune(BranchPruneRequest(run_id="run-phase27", relative_threshold=0.5))
        branch_component_scores, _classes = dag_service.collect_branch_component_scores("run-phase27", state_store)
        merge_result = merge_service.merge_with_complementarity(
            BranchMergeRequest(run_id="run-phase27", minimum_quality=0.2),
            branch_component_scores,
        )

        assert explore_result.sharing_candidate_ids
        assert "branch-peer" in prune_result.pruned_branch_ids
        assert merge_result.outcome.merged_branch_id == "branch-primary"

    def test_branch_component_scores_flow_from_persisted_hypothesis_specs(self, tmp_path: Path) -> None:
        state_store, dag_service, _share_service, _prune_service, _merge_service, _multi_branch_service, _merger, _dispatches = _build_phase27_context(
            tmp_path,
            current_round=1,
        )

        branch_component_scores, branch_component_classes = dag_service.collect_branch_component_scores(
            "run-phase27",
            state_store,
        )

        assert branch_component_classes["branch-primary"] == {"model"}
        assert branch_component_classes["branch-novel"] == {"workflow"}
        assert "workflow" in branch_component_scores["branch-novel"]
