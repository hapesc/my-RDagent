"""FC-2 branch pruning - score-based MCTS natural selection."""

from __future__ import annotations

import logging

from data_models import BranchState, ExplorationGraph

_log = logging.getLogger(__name__)


class BranchPruner:
    """Prunes underperforming branches based on score thresholds.

    Uses "MCTS natural selection" semantics: branches scoring below a relative
    threshold of the best branch get pruned.

    Safety invariants:
    - The best active scored node is never pruned.
    - At least one active branch remains.
    """

    def __init__(
        self,
        score_threshold: float | None = None,
        relative_threshold: float | None = 0.5,
    ) -> None:
        self._score_threshold = score_threshold
        self._relative_threshold = relative_threshold

    def _compute_cutoff(self, best_score: float) -> float:
        cutoff = float("-inf")
        if self._score_threshold is not None:
            cutoff = max(cutoff, self._score_threshold)
        if self._relative_threshold is not None:
            cutoff = max(cutoff, best_score * self._relative_threshold)
        return cutoff

    def prune(self, graph: ExplorationGraph) -> ExplorationGraph:
        """Mark underperforming branches as PRUNED in-place and return graph."""
        active_nodes = [node for node in graph.nodes if node.branch_state == BranchState.ACTIVE]

        if len(active_nodes) <= 1:
            return graph

        scored_active_nodes = [node for node in active_nodes if node.score is not None]
        if not scored_active_nodes:
            _log.debug("No scored active nodes - skipping pruning")
            return graph

        scored_values = [node.score for node in scored_active_nodes if node.score is not None]
        best_score = max(scored_values)
        best_node_ids = {node.node_id for node in scored_active_nodes if node.score == best_score}
        cutoff = self._compute_cutoff(best_score)

        pruned_count = 0
        for node in active_nodes:
            if node.node_id in best_node_ids:
                continue
            if node.score is None:
                continue
            if node.score >= cutoff:
                continue

            remaining_active = sum(
                1
                for existing in graph.nodes
                if existing.branch_state == BranchState.ACTIVE and existing.node_id != node.node_id
            )
            if remaining_active < 1:
                _log.debug("Skipping prune of %s - would leave 0 active nodes", node.node_id)
                continue

            node.branch_state = BranchState.PRUNED
            if node.node_id in graph.branch_states:
                graph.branch_states[node.node_id] = BranchState.PRUNED
            pruned_count += 1
            _log.debug(
                "Pruned node %s (score=%.4f, cutoff=%.4f)",
                node.node_id,
                node.score,
                cutoff,
            )

        _log.info(
            "Pruning complete: %d nodes pruned, %d remain active",
            pruned_count,
            len(active_nodes) - pruned_count,
        )
        return graph

    def should_prune(self, graph: ExplorationGraph, node_id: str) -> bool:
        """Return whether a specific node should be pruned."""
        target = None
        for node in graph.nodes:
            if node.node_id == node_id:
                target = node
                break

        if target is None or target.score is None:
            return False
        if target.branch_state != BranchState.ACTIVE:
            return False

        active_scored = [
            node for node in graph.nodes if node.branch_state == BranchState.ACTIVE and node.score is not None
        ]
        if len(active_scored) <= 1:
            return False

        scored_values = [node.score for node in active_scored if node.score is not None]
        best_score = max(scored_values)
        if target.score == best_score:
            return False

        cutoff = self._compute_cutoff(best_score)
        return target.score < cutoff
