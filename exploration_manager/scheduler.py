"""FC-2 MCTS/PUCT trace scheduler per RDAgent paper Algorithm 1."""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional

from data_models import BranchState, ExplorationGraph

_log = logging.getLogger(__name__)


class MCTSScheduler:
    """MCTS/PUCT-based node selection for multi-branch exploration.

    Uses the PUCT formula to balance exploration (unvisited nodes) vs
    exploitation (high-scoring nodes):

        PUCT(node) = Q(node) + c * sqrt(ln(N_parent) / N_node)

    where:
        Q(node) = node's score (exploitation term)
        c = exploration_weight (default sqrt(2) ~= 1.41, standard UCB1)
        N_parent = total visits across all nodes (or parent visit count)
        N_node = visit count of this node
    """

    def __init__(self, exploration_weight: float = 1.41) -> None:
        self._c = exploration_weight

    def select_node(self, graph: ExplorationGraph) -> Optional[str]:
        """Select the best node to expand using PUCT formula.

        Returns node_id of best node to expand, or None if no expandable nodes.
        Unvisited ACTIVE nodes get infinite priority (always explored first).
        Only ACTIVE nodes are considered (PRUNED/MERGED nodes skipped).
        """
        active_nodes = [n for n in graph.nodes if n.branch_state == BranchState.ACTIVE]
        if not active_nodes:
            return None

        total_visits = sum(graph.visit_counts.get(n.node_id, 0) for n in active_nodes)

        unvisited = [n for n in active_nodes if graph.visit_counts.get(n.node_id, 0) == 0]
        if unvisited:
            no_score = [n for n in unvisited if n.score is None]
            if no_score:
                return no_score[0].node_id
            return unvisited[0].node_id

        best_node_id: Optional[str] = None
        best_puct = float("-inf")

        for node in active_nodes:
            n_visits = graph.visit_counts.get(node.node_id, 0)
            q_value = node.score if node.score is not None else 0.0

            if n_visits > 0 and total_visits > 0:
                exploration_bonus = self._c * math.sqrt(math.log(total_visits) / n_visits)
            else:
                exploration_bonus = float("inf")

            puct_score = q_value + exploration_bonus
            _log.debug(
                "PUCT(%s) = %.4f (Q=%.4f, bonus=%.4f, visits=%d)",
                node.node_id,
                puct_score,
                q_value,
                exploration_bonus,
                n_visits,
            )

            if puct_score > best_puct:
                best_puct = puct_score
                best_node_id = node.node_id

        return best_node_id

    def update_visit_count(self, graph: ExplorationGraph, node_id: str) -> ExplorationGraph:
        """Increment visit count for a node after it has been selected/expanded."""
        current = graph.visit_counts.get(node_id, 0)
        graph.visit_counts[node_id] = current + 1
        return graph

    def get_all_scores(self, graph: ExplorationGraph) -> Dict[str, float]:
        """Return node_id -> PUCT score map for debugging/logging."""
        active_nodes = [n for n in graph.nodes if n.branch_state == BranchState.ACTIVE]
        if not active_nodes:
            return {}

        total_visits = sum(graph.visit_counts.get(n.node_id, 0) for n in active_nodes)
        scores: Dict[str, float] = {}

        for node in active_nodes:
            n_visits = graph.visit_counts.get(node.node_id, 0)
            q_value = node.score if node.score is not None else 0.0

            if n_visits > 0 and total_visits > 0:
                exploration_bonus = self._c * math.sqrt(math.log(total_visits) / n_visits)
            else:
                exploration_bonus = float("inf")

            scores[node.node_id] = q_value + exploration_bonus

        return scores
