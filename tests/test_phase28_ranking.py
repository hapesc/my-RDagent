from __future__ import annotations

import pytest
from pydantic import ValidationError

from rd_agent.algorithms.holdout import collect_candidate_ids, filter_by_quality_threshold, rank_candidates
from rd_agent.contracts.exploration import (
    CandidateRankEntry,
    DAGEdgeSnapshot,
    DAGNodeSnapshot,
    EdgeType,
    FinalSubmissionSnapshot,
    NodeMetrics,
)


def _node(node_id: str, branch_id: str, validation_score: float) -> DAGNodeSnapshot:
    return DAGNodeSnapshot(
        node_id=node_id,
        run_id="run-phase28",
        branch_id=branch_id,
        parent_node_ids=[],
        depth=0,
        node_metrics=NodeMetrics(validation_score=validation_score),
    )


def test_node_metrics_backward_compatible_defaults() -> None:
    metrics = NodeMetrics()

    assert metrics.validation_score == 0.0
    assert metrics.holdout_mean == 0.0
    assert metrics.holdout_std == 0.0


def test_node_metrics_holdout_round_trip() -> None:
    metrics = NodeMetrics(holdout_mean=0.85, holdout_std=0.02)

    dumped = metrics.model_dump()
    restored = NodeMetrics.model_validate(dumped)

    assert restored == metrics


def test_node_metrics_rejects_negative_holdout_mean() -> None:
    with pytest.raises(ValidationError):
        NodeMetrics(holdout_mean=-0.1)


def test_candidate_rank_entry_validates_rank() -> None:
    entry = CandidateRankEntry(
        node_id="node-1",
        branch_id="branch-a",
        rank=1,
        holdout_mean=0.9,
        holdout_std=0.01,
    )

    assert entry.rank == 1

    with pytest.raises(ValidationError):
        CandidateRankEntry(
            node_id="node-1",
            branch_id="branch-a",
            rank=0,
            holdout_mean=0.9,
            holdout_std=0.01,
        )


def test_final_submission_snapshot_constructs() -> None:
    ranked_candidates = [
        CandidateRankEntry(
            node_id="node-1",
            branch_id="branch-a",
            rank=1,
            holdout_mean=0.9,
            holdout_std=0.01,
        )
    ]

    submission = FinalSubmissionSnapshot(
        submission_id="submission-1",
        run_id="run-phase28",
        winner_node_id="node-1",
        winner_branch_id="branch-a",
        holdout_mean=0.9,
        holdout_std=0.01,
        ranked_candidates=ranked_candidates,
        ancestry_chain=["parent-1", "parent-2"],
    )

    assert submission.ranked_candidates == ranked_candidates
    assert submission.ancestry_chain == ["parent-1", "parent-2"]


def test_rank_candidates_prefers_higher_mean_then_lower_std() -> None:
    ranked = rank_candidates(
        {
            "node-1": [0.9, 0.8],
            "node-2": [0.85, 0.85],
            "node-3": [0.9, 0.9],
        }
    )

    assert ranked[0][0] == "node-3"
    assert ranked[1][0] == "node-1"
    assert ranked[2][0] == "node-2"


def test_rank_candidates_single_fold_has_zero_std() -> None:
    ranked = rank_candidates({"node-1": [0.77]})

    assert ranked == [("node-1", 0.77, 0.0)]


def test_rank_candidates_empty_scores_returns_empty_list() -> None:
    assert rank_candidates({}) == []


def test_filter_by_quality_threshold_keeps_candidates_at_or_above_median() -> None:
    candidates = [
        _node("node-1", "branch-a", 0.9),
        _node("node-2", "branch-b", 0.7),
        _node("node-3", "branch-c", 0.5),
        _node("node-4", "branch-d", 0.3),
    ]

    filtered = filter_by_quality_threshold(candidates)

    assert [candidate.node_id for candidate in filtered] == ["node-1", "node-2"]


def test_filter_by_quality_threshold_single_candidate_returns_itself() -> None:
    candidate = _node("node-1", "branch-a", 0.9)

    assert filter_by_quality_threshold([candidate]) == [candidate]


def test_filter_by_quality_threshold_empty_list_returns_empty_list() -> None:
    assert filter_by_quality_threshold([]) == []


def test_collect_candidate_ids_unions_frontier_and_merged_targets() -> None:
    all_nodes = [
        _node("node-1", "branch-a", 0.9),
        _node("node-2", "branch-b", 0.8),
        _node("node-3", "branch-c", 0.7),
    ]
    all_edges = [
        DAGEdgeSnapshot(source_node_id="node-1", target_node_id="node-2", edge_type=EdgeType.PARENT),
        DAGEdgeSnapshot(source_node_id="node-2", target_node_id="node-3", edge_type=EdgeType.MERGED),
        DAGEdgeSnapshot(source_node_id="node-1", target_node_id="node-3", edge_type=EdgeType.SHARED),
    ]

    candidate_ids = collect_candidate_ids(all_nodes, all_edges, {"node-1", "node-3"})

    assert candidate_ids == {"node-1", "node-3"}
