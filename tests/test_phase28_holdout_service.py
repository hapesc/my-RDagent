from __future__ import annotations

from pathlib import Path

from v3.contracts.exploration import EdgeType, FinalSubmissionSnapshot, NodeMetrics
from v3.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.dag_service import DAGService
from v3.orchestration.holdout_validation_service import HoldoutValidationService
from v3.ports.holdout_port import StubHoldoutSplitPort
from v3.ports.state_store import ArtifactRecord, StateStorePort


class _CountingEvaluationPort:
    def __init__(self, scores: dict[str, float]) -> None:
        self._scores = scores
        self.calls: list[tuple[str, int]] = []

    def evaluate(self, *, candidate_node_id: str, fold) -> float:
        self.calls.append((candidate_node_id, fold.fold_index))
        return self._scores.get(candidate_node_id, 0.5)


def _write_run(state_store: ArtifactStateStore, *, run_id: str) -> None:
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id=run_id,
            title="Phase 28 holdout service",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            branch_ids=[],
            highlighted_artifact_ids=[],
            summary="Holdout service test run.",
        )
    )


def _build_service(
    tmp_path: Path,
    *,
    run_id: str,
    evaluation_scores: dict[str, float],
) -> tuple[ArtifactStateStore, DAGService, HoldoutValidationService, _CountingEvaluationPort]:
    state_store = ArtifactStateStore(tmp_path / "state")
    _write_run(state_store, run_id=run_id)
    dag_service = DAGService(state_store)
    evaluation_port = _CountingEvaluationPort(evaluation_scores)
    service = HoldoutValidationService(
        state_store=state_store,
        dag_service=dag_service,
        split_port=StubHoldoutSplitPort(k=5),
        evaluation_port=evaluation_port,
    )
    return state_store, dag_service, service, evaluation_port


def test_finalize_filters_candidates_ranks_and_persists_submission(tmp_path: Path) -> None:
    run_id = "run-phase28-filter"
    state_store, dag_service, service, evaluation_port = _build_service(
        tmp_path,
        run_id=run_id,
        evaluation_scores={},
    )
    candidates = [
        dag_service.create_node(
            run_id=run_id,
            branch_id=f"branch-{label}",
            node_metrics=NodeMetrics(validation_score=score),
        )
        for label, score in (("a", 0.9), ("b", 0.8), ("c", 0.7), ("d", 0.6))
    ]
    evaluation_port._scores = {
        candidates[0].node_id: 0.91,
        candidates[1].node_id: 0.86,
        candidates[2].node_id: 0.4,
        candidates[3].node_id: 0.3,
    }

    submission = service.finalize(run_id=run_id)

    assert submission.winner_node_id == candidates[0].node_id
    assert [entry.node_id for entry in submission.ranked_candidates] == [
        candidates[0].node_id,
        candidates[1].node_id,
    ]
    assert len(evaluation_port.calls) == 10
    assert state_store.load_final_submission(run_id) == submission


def test_finalize_single_candidate_returns_zero_std_and_ancestry(tmp_path: Path) -> None:
    run_id = "run-phase28-single"
    state_store, dag_service, service, evaluation_port = _build_service(
        tmp_path,
        run_id=run_id,
        evaluation_scores={},
    )
    parent = dag_service.create_node(
        run_id=run_id,
        branch_id="branch-parent",
        node_metrics=NodeMetrics(validation_score=0.5),
    )
    winner = dag_service.create_node(
        run_id=run_id,
        branch_id="branch-winner",
        parent_node_ids=[parent.node_id],
        node_metrics=NodeMetrics(validation_score=0.9),
    )
    evaluation_port._scores = {winner.node_id: 0.88}

    submission = service.finalize(run_id=run_id)

    assert submission.winner_node_id == winner.node_id
    assert submission.holdout_std == 0.0
    assert submission.ancestry_chain == [parent.node_id]


def test_finalize_includes_merged_nodes_beyond_frontier_and_updates_metrics(tmp_path: Path) -> None:
    run_id = "run-phase28-merged"
    state_store, dag_service, service, evaluation_port = _build_service(
        tmp_path,
        run_id=run_id,
        evaluation_scores={},
    )
    node_a = dag_service.create_node(
        run_id=run_id,
        branch_id="branch-a",
        node_metrics=NodeMetrics(validation_score=0.9),
    )
    node_b = dag_service.create_node(
        run_id=run_id,
        branch_id="branch-b",
        node_metrics=NodeMetrics(validation_score=0.82),
    )
    merged = dag_service.create_node(
        run_id=run_id,
        branch_id="branch-merged",
        node_metrics=NodeMetrics(validation_score=0.88),
    )
    dag_service.create_typed_edge(
        source_node_id=node_a.node_id,
        target_node_id=merged.node_id,
        edge_type=EdgeType.MERGED,
    )
    dag_service.create_typed_edge(
        source_node_id=node_b.node_id,
        target_node_id=merged.node_id,
        edge_type=EdgeType.MERGED,
    )
    dag_service.create_node(
        run_id=run_id,
        branch_id="branch-child",
        parent_node_ids=[merged.node_id],
        node_metrics=NodeMetrics(validation_score=0.81),
    )
    evaluation_port._scores = {
        node_a.node_id: 0.8,
        node_b.node_id: 0.7,
        merged.node_id: 0.95,
    }

    submission = service.finalize(run_id=run_id)
    merged_after = state_store.load_dag_node(merged.node_id)

    assert merged.node_id in {entry.node_id for entry in submission.ranked_candidates}
    assert submission.winner_node_id == merged.node_id
    assert merged_after is not None
    assert merged_after.node_metrics.holdout_mean == 0.95
    assert merged_after.node_metrics.holdout_std == 0.0


def test_artifact_state_store_round_trips_final_submission(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    submission = FinalSubmissionSnapshot(
        submission_id="submission-1",
        run_id="run-phase28-roundtrip",
        winner_node_id="node-1",
        winner_branch_id="branch-a",
        holdout_mean=0.9,
        holdout_std=0.01,
        ranked_candidates=[],
        ancestry_chain=[],
    )

    record = state_store.write_final_submission(submission)
    loaded = state_store.load_final_submission(submission.run_id)

    assert isinstance(record, ArtifactRecord)
    assert loaded == submission
    assert "write_final_submission" in dir(StateStorePort)
    assert "load_final_submission" in dir(StateStorePort)
