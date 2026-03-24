"""Pure holdout validation algorithms for Phase 28."""

from __future__ import annotations

import statistics

from v3.contracts.exploration import DAGEdgeSnapshot, DAGNodeSnapshot, EdgeType


def rank_candidates(candidate_scores: dict[str, list[float]]) -> list[tuple[str, float, float]]:
    """Rank by mean holdout score descending, then by std ascending."""

    if not candidate_scores:
        return []

    entries: list[tuple[str, float, float]] = []
    for node_id, fold_scores in candidate_scores.items():
        if not fold_scores:
            raise ValueError(f"candidate {node_id} has no fold scores")
        mean_score = statistics.mean(fold_scores)
        std_score = statistics.stdev(fold_scores) if len(fold_scores) > 1 else 0.0
        entries.append((node_id, mean_score, std_score))

    entries.sort(key=lambda entry: (-entry[1], entry[2]))
    return entries


def filter_by_quality_threshold(candidates: list[DAGNodeSnapshot]) -> list[DAGNodeSnapshot]:
    """Filter candidates below the median validation_score."""

    if len(candidates) <= 1:
        return list(candidates)

    threshold = statistics.median(candidate.node_metrics.validation_score for candidate in candidates)
    return [
        candidate
        for candidate in candidates
        if candidate.node_metrics.validation_score >= threshold
    ]


def collect_candidate_ids(
    all_nodes: list[DAGNodeSnapshot],
    all_edges: list[DAGEdgeSnapshot],
    frontier_ids: set[str],
) -> set[str]:
    """Collect frontier + MERGED target node IDs, constrained to known nodes."""

    existing_node_ids = {node.node_id for node in all_nodes}
    merged_target_ids = {
        edge.target_node_id
        for edge in all_edges
        if edge.edge_type == EdgeType.MERGED and edge.target_node_id in existing_node_ids
    }
    return {node_id for node_id in frontier_ids if node_id in existing_node_ids} | merged_target_ids


def collect_candidates(
    all_nodes: list[DAGNodeSnapshot],
    all_edges: list[DAGEdgeSnapshot],
    frontier_ids: set[str],
) -> set[str]:
    """Backward-compatible alias for plan text that still says collect_candidates."""

    return collect_candidate_ids(all_nodes, all_edges, frontier_ids)


__all__ = ["collect_candidate_ids", "filter_by_quality_threshold", "rank_candidates"]
