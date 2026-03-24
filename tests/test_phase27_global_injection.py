from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import (
    ApproachCategory,
    BranchDecisionKind,
    EdgeType,
    ExplorationMode,
    HypothesisSpec,
    MergeOutcomeSnapshot,
    NodeMetrics,
)
from v3.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import BranchFallbackResult, BranchMergeResult, ConvergeRoundRequest, ExploreRoundRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_lifecycle_service import BranchLifecycleService
from v3.orchestration.branch_merge_service import BranchMergeService
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
        run_id="run-share",
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


class _ExplodingEmbeddingPort:
    def embed(self, texts: list[str]) -> list[list[float]]:
        from v3.ports.embedding_port import EmbeddingUnavailableError

        raise EmbeddingUnavailableError("embedding service unavailable")


class _FakeShareService:
    def __init__(self, *, global_best_id: str | None, candidate_map: dict[str, list[str]]) -> None:
        self._global_best_id = global_best_id
        self._candidate_map = candidate_map

    def identify_global_best(self, run_id: str) -> str | None:
        return self._global_best_id

    def compute_sharing_candidates(
        self,
        *,
        run_id: str,
        target_branch_id: str,
        current_round: int,
        budget_ratio: float,
    ) -> list[str]:
        return list(self._candidate_map.get(target_branch_id, []))


class _MergeSpy:
    def __init__(self, board_service: BranchBoardService) -> None:
        self._board_service = board_service
        self.called_with_complementarity = False
        self.branch_component_scores: dict[str, dict[str, float]] | None = None

    def merge_with_complementarity(self, request, branch_component_scores):
        self.called_with_complementarity = True
        self.branch_component_scores = branch_component_scores
        outcome = MergeOutcomeSnapshot(
            outcome_id="merge-outcome-phase27",
            run_id=request.run_id,
            summary="Merged with complementarity.",
            rationale="Complementary merge path selected.",
            merged_branch_id="branch-primary",
            source_branch_ids=list(branch_component_scores.keys()),
            shortlist=[],
        )
        return BranchMergeResult(
            outcome=outcome,
            board=self._board_service.get_board(request.run_id),
        )

    def merge(self, request):
        outcome = MergeOutcomeSnapshot(
            outcome_id="merge-outcome-fallback",
            run_id=request.run_id,
            summary="Merged without complementarity.",
            rationale="Fallback merge path selected.",
            merged_branch_id="branch-primary",
            source_branch_ids=["branch-primary"],
            shortlist=[],
        )
        return BranchMergeResult(
            outcome=outcome,
            board=self._board_service.get_board(request.run_id),
        )

    def fallback(self, request):
        return BranchFallbackResult(
            selected_branch_id="branch-primary",
            rationale="fallback",
            shortlist=[],
        )


def _write_component_spec(
    state_store: ArtifactStateStore,
    *,
    branch_id: str,
    label: str,
    component: str,
) -> None:
    state_store.write_hypothesis_spec(
        branch_id,
        HypothesisSpec(
            label=label,
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="sharing",
            rationale="seeded for phase 27",
            component_classes=(component,),
        ),
    )


def _build_multi_branch_service(
    tmp_path: Path,
    *,
    current_round: int,
    share_service=None,
    merge_service=None,
):
    state_store = ArtifactStateStore(tmp_path / "state")
    workspace_manager = BranchWorkspaceManager(tmp_path / "state")
    board_service = BranchBoardService(state_store)
    run_board_service = RunBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    dag_service = DAGService(state_store)
    primary = _branch("branch-primary", "primary", 0.92)
    peer = _branch("branch-peer", "peer", 0.73)
    for branch in (primary, peer):
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-share",
            title="Phase 27 share run",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            exploration_mode=ExplorationMode.EXPLORATION,
            branch_ids=[primary.branch_id, peer.branch_id],
            primary_branch_id=primary.branch_id,
            highlighted_artifact_ids=[],
            summary="Share summary.",
            current_round=current_round,
            max_rounds=4,
        )
    )
    _write_component_spec(state_store, branch_id=primary.branch_id, label=primary.label, component="model")
    _write_component_spec(state_store, branch_id=peer.branch_id, label=peer.label, component="ensemble")
    dag_service.create_node(
        run_id="run-share",
        branch_id=primary.branch_id,
        node_metrics=NodeMetrics(validation_score=0.92, complementarity_score=0.10, diversity_score=0.20),
    )
    dag_service.create_node(
        run_id="run-share",
        branch_id=peer.branch_id,
        node_metrics=NodeMetrics(validation_score=0.73, complementarity_score=0.90, diversity_score=0.80),
    )
    dispatches: list[dict[str, object]] = []
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
        branch_merge_service=merge_service
        or BranchMergeService(
            state_store=state_store,
            convergence_service=convergence_service,
            board_service=board_service,
        ),
        dispatcher=lambda payload: dispatches.append(payload),
        dag_service=dag_service,
        branch_share_service=share_service,
    )
    return state_store, dag_service, board_service, service, dispatches


def test_shared_edge_create_typed_edge_persists_shared_edge(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)
    source = service.create_node(run_id="run-001", branch_id="branch-source")
    target = service.create_node(run_id="run-001", branch_id="branch-target")

    edge = service.create_typed_edge(
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        edge_type=EdgeType.SHARED,
        weight=0.42,
    )

    assert edge.edge_type is EdgeType.SHARED
    assert edge.weight == pytest.approx(0.42)
    assert state_store.list_dag_edges("run-001") == [edge]


def test_shared_edge_create_typed_edge_persists_merged_edge(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)
    source = service.create_node(run_id="run-001", branch_id="branch-source")
    target = service.create_node(run_id="run-001", branch_id="branch-target")

    edge = service.create_typed_edge(
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        edge_type=EdgeType.MERGED,
    )

    assert edge.edge_type is EdgeType.MERGED
    assert state_store.list_dag_edges("run-001") == [edge]


def test_shared_edge_create_typed_edge_rejects_missing_source_node(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)
    target = service.create_node(run_id="run-001", branch_id="branch-target")

    with pytest.raises(KeyError, match="source node not found: missing-source"):
        service.create_typed_edge(
            source_node_id="missing-source",
            target_node_id=target.node_id,
            edge_type=EdgeType.SHARED,
        )


def test_shared_edge_create_shared_edge_rejects_missing_source_node(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)
    target = service.create_node(run_id="run-001", branch_id="branch-target")

    with pytest.raises(KeyError, match="source node not found: missing-source"):
        service.create_shared_edge(
            source_node_id="missing-source",
            target_node_id=target.node_id,
        )


def test_identify_global_best_picks_highest_frontier_branch(tmp_path: Path) -> None:
    state_store, dag_service, _board_service, _service, _dispatches = _build_multi_branch_service(
        tmp_path,
        current_round=1,
    )
    share_service = BranchShareService(
        state_store=state_store,
        memory_service=MagicMock(),
        dag_service=dag_service,
        embedding_port=_StaticEmbeddingPort(
            {
                "primary": [1.0, 0.0],
                "peer": [0.8, 0.2],
            }
        ),
    )

    assert share_service.identify_global_best("run-share") == "branch-primary"


def test_compute_sharing_candidates_skips_round_zero_and_embedding_failures(tmp_path: Path) -> None:
    state_store, dag_service, _board_service, _service, _dispatches = _build_multi_branch_service(
        tmp_path,
        current_round=1,
    )
    round_zero_service = BranchShareService(
        state_store=state_store,
        memory_service=MagicMock(),
        dag_service=dag_service,
        embedding_port=_StaticEmbeddingPort({"primary": [1.0, 0.0], "peer": [0.8, 0.2]}),
    )
    exploding_service = BranchShareService(
        state_store=state_store,
        memory_service=MagicMock(),
        dag_service=dag_service,
        embedding_port=_ExplodingEmbeddingPort(),
    )

    assert round_zero_service.compute_sharing_candidates(
        run_id="run-share",
        target_branch_id="branch-primary",
        current_round=0,
        budget_ratio=0.25,
    ) == []
    assert exploding_service.compute_sharing_candidates(
        run_id="run-share",
        target_branch_id="branch-primary",
        current_round=1,
        budget_ratio=0.25,
    ) == []


def test_compute_sharing_candidates_uses_interaction_kernel_and_skips_self(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_store, dag_service, _board_service, _service, _dispatches = _build_multi_branch_service(
        tmp_path,
        current_round=1,
    )
    third = _branch("branch-third", "third", 0.88)
    state_store.write_branch_snapshot(third)
    run = state_store.load_run_snapshot("run-share")
    assert run is not None
    state_store.write_run_snapshot(run.model_copy(update={"branch_ids": [*run.branch_ids, third.branch_id]}))
    dag_service.create_node(
        run_id="run-share",
        branch_id=third.branch_id,
        node_metrics=NodeMetrics(validation_score=0.88, complementarity_score=0.40, diversity_score=0.30),
    )
    share_service = BranchShareService(
        state_store=state_store,
        memory_service=MagicMock(),
        dag_service=dag_service,
        embedding_port=_StaticEmbeddingPort(
            {
                "primary": [1.0, 0.0],
                "peer": [0.9, 0.1],
                "third": [0.0, 1.0],
            }
        ),
    )

    def fake_choices(population: list[str], *, weights: list[float] | None = None, k: int) -> list[str]:
        assert "branch-primary" not in population
        assert population == ["branch-peer", "branch-third"]
        assert weights is not None
        return ["branch-peer"]

    monkeypatch.setattr("v3.algorithms.interaction_kernel.random.choices", fake_choices)

    assert share_service.compute_sharing_candidates(
        run_id="run-share",
        target_branch_id="branch-primary",
        current_round=1,
        budget_ratio=0.25,
    ) == ["branch-peer"]


def test_multi_branch_service_records_sharing_candidates_edges_and_decisions(tmp_path: Path) -> None:
    share_service = _FakeShareService(
        global_best_id="branch-primary",
        candidate_map={
            "branch-primary": ["branch-peer"],
            "branch-peer": ["branch-primary"],
        },
    )
    state_store, _dag_service, _board_service, service, dispatches = _build_multi_branch_service(
        tmp_path,
        current_round=1,
        share_service=share_service,
    )

    result = service.run_exploration_round(
        ExploreRoundRequest(
            run_id="run-share",
            hypotheses=["primary", "peer"],
            auto_prune=False,
        )
    )

    decisions = state_store.list_branch_decisions("run-share")
    edges = state_store.list_dag_edges("run-share")

    assert set(result.sharing_candidate_ids) == {"branch-primary", "branch-peer"}
    assert all("sharing_candidate_ids" in payload for payload in dispatches)
    assert any(decision.kind is BranchDecisionKind.SHARE for decision in decisions)
    assert any(edge.edge_type is EdgeType.SHARED for edge in edges)


def test_multi_branch_service_uses_complementary_merge_path_when_available(tmp_path: Path) -> None:
    share_service = _FakeShareService(global_best_id="branch-primary", candidate_map={})
    state_store = ArtifactStateStore(tmp_path / "state")
    board_service = BranchBoardService(state_store)
    merge_spy = _MergeSpy(board_service)
    _state_store, _dag_service, _board_service, service, _dispatches = _build_multi_branch_service(
        tmp_path,
        current_round=1,
        share_service=share_service,
        merge_service=merge_spy,
    )

    result = service.run_convergence_round(ConvergeRoundRequest(run_id="run-share", minimum_quality=0.7))

    assert merge_spy.called_with_complementarity is True
    assert merge_spy.branch_component_scores is not None
    assert result.selected_branch_id == "branch-primary"
