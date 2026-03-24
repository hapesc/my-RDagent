from __future__ import annotations

from pathlib import Path

import pytest

from v3.algorithms.merge import LLMTraceMerger, MergeDesign, SimpleTraceMerger
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import EdgeType
from v3.contracts.run import RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import BranchMergeRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.convergence_service import ConvergenceService
from v3.orchestration.dag_service import DAGService


def _branch(branch_id: str, *, quality: float) -> BranchSnapshot:
    stage = StageSnapshot(
        stage_key=StageKey.VERIFY,
        status=StageStatus.COMPLETED,
        summary=f"{branch_id} verified.",
        next_stage_key=StageKey.SYNTHESIZE,
    )
    return BranchSnapshot(
        branch_id=branch_id,
        run_id="run-merge",
        label=f"{branch_id} hypothesis",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.VERIFY,
        stages=[stage],
        score=BranchScore(
            exploration_priority=quality,
            result_quality=quality,
            rationale=f"{branch_id} quality {quality:.2f}.",
        ),
        lineage=BranchLineage(source_summary=f"Evidence for {branch_id}."),
        artifact_ids=[],
    )


def _seed_run(state_store: ArtifactStateStore, dag_service: DAGService) -> list[BranchSnapshot]:
    branches = [
        _branch("branch-a", quality=0.91),
        _branch("branch-b", quality=0.84),
        _branch("branch-c", quality=0.79),
    ]
    for branch in branches:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-merge",
            title="Merge board",
            status=RunStatus.ACTIVE,
            branch_ids=[branch.branch_id for branch in branches],
            primary_branch_id=branches[0].branch_id,
            highlighted_artifact_ids=[],
            summary="Merge summary.",
        )
    )
    for index, branch in enumerate(branches, start=1):
        dag_service.create_node(
            run_id="run-merge",
            branch_id=branch.branch_id,
            node_metrics={"validation_score": 0.6 + index * 0.1},
        )
    return branches


class _CapturingMerger:
    def __init__(self, *, holdout_score: float | None = None) -> None:
        self.holdout_score = holdout_score
        self.traces: list[dict] | None = None

    def merge(self, traces: list[dict], task_summary: str, scenario_name: str) -> MergeDesign:
        self.traces = traces
        return MergeDesign(
            summary=f"Complementary synthesis for {scenario_name}",
            operation="create",
            source_branch_ids=tuple(trace["branch_id"] for trace in traces),
            component_analysis="captured",
            holdout_score=self.holdout_score,
        )


def test_llm_trace_merger_emits_operation_sources_and_analysis() -> None:
    merger = LLMTraceMerger()

    result = merger.merge(
        traces=[
            {"branch_id": "branch-a", "design": {"summary": "model-heavy"}, "components": {"model": 0.9}},
            {"branch_id": "branch-b", "design": {"summary": "ensemble-heavy"}, "components": {"ensemble": 0.9}},
        ],
        task_summary="merge",
        scenario_name="phase27",
    )

    assert result.operation == "create"
    assert result.source_branch_ids == ("branch-a", "branch-b")
    assert "trace-0" in result.component_analysis


def test_llm_trace_merger_handles_empty_traces() -> None:
    merger = LLMTraceMerger()

    result = merger.merge(traces=[], task_summary="merge", scenario_name="phase27")

    assert result.operation == "select"
    assert "No traces to merge" in result.summary


def test_simple_trace_merger_remains_backward_compatible() -> None:
    merger = SimpleTraceMerger()

    result = merger.merge([{"design": {"summary": "test"}}], "task", "scenario")

    assert result.summary == "test"

def test_merge_with_complementarity_selects_best_pair_and_creates_merged_edges(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    _seed_run(state_store, dag_service)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    merge_service = BranchMergeService(
        state_store=state_store,
        convergence_service=convergence_service,
        board_service=board_service,
        merger=LLMTraceMerger(),
        dag_service=dag_service,
    )

    result = merge_service.merge_with_complementarity(
        BranchMergeRequest(run_id="run-merge", minimum_quality=0.7),
        {
            "branch-a": {"model": 0.9, "feature_eng": 0.2},
            "branch-b": {"model": 0.2, "ensemble": 0.9},
            "branch-c": {"model": 0.8, "feature_eng": 0.1},
        },
    )

    edges = state_store.list_dag_edges("run-merge")

    assert result.outcome.merged_branch_id == "branch-a"
    assert result.outcome.source_branch_ids == ["branch-a", "branch-b"]
    assert "phase27-complementary-merge" in result.outcome.summary
    assert sum(1 for edge in edges if edge.edge_type is EdgeType.MERGED) == 2


def test_merge_with_complementarity_rejects_underperforming_holdout(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    _seed_run(state_store, dag_service)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    merge_service = BranchMergeService(
        state_store=state_store,
        convergence_service=convergence_service,
        board_service=board_service,
        merger=_CapturingMerger(holdout_score=0.70),
        dag_service=dag_service,
    )

    result = merge_service.merge_with_complementarity(
        BranchMergeRequest(run_id="run-merge", minimum_quality=0.7),
        {
            "branch-a": {"model": 0.9},
            "branch-b": {"ensemble": 0.9},
        },
    )

    assert result.outcome.failure_reason == "holdout_validation_failed"


def test_merge_with_complementarity_filters_weak_components_and_resolves_conflicts(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    _seed_run(state_store, dag_service)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    merger = _CapturingMerger()
    merge_service = BranchMergeService(
        state_store=state_store,
        convergence_service=convergence_service,
        board_service=board_service,
        merger=merger,
        dag_service=dag_service,
    )

    merge_service.merge_with_complementarity(
        BranchMergeRequest(run_id="run-merge", minimum_quality=0.8),
        {
            "branch-a": {"model": 0.9, "weak": 0.2},
            "branch-b": {"model": 0.8, "ensemble": 0.95},
        },
    )

    assert merger.traces is not None
    assert merger.traces[0]["components"] == {"model": 0.9}
    assert merger.traces[1]["components"] == {"ensemble": 0.95}
