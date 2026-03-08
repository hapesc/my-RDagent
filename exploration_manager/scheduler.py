"""FC-2 MCTS/PUCT trace scheduler per RDAgent paper Algorithm 1."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from data_models import BranchState, ExplorationGraph, NodeRecord
from exploration_manager.reward import RewardCalculator


class MCTSScheduler:
    """MCTS/PUCT-based node selection and value backup."""

    def __init__(
        self,
        c_puct: float = 1.41,
        reward_calculator: Optional[RewardCalculator] = None,
        **legacy_kwargs: Any,
    ) -> None:
        if "exploration_weight" in legacy_kwargs:
            c_puct = float(legacy_kwargs.pop("exploration_weight"))
        if legacy_kwargs:
            unexpected = ", ".join(sorted(legacy_kwargs.keys()))
            raise TypeError(f"Unexpected keyword argument(s): {unexpected}")

        self._c_puct = c_puct
        self._reward_calculator = reward_calculator or RewardCalculator()

    def select_node(self, graph: ExplorationGraph) -> Optional[str]:
        """Select one ACTIVE node by paper-faithful PUCT."""
        active_nodes = [n for n in graph.nodes if n.branch_state == BranchState.ACTIVE]
        if not active_nodes:
            return None

        unvisited = [n for n in active_nodes if n.visits == 0]
        if unvisited:
            unvisited_no_score = [n for n in unvisited if n.score is None]
            if unvisited_no_score:
                return unvisited_no_score[0].node_id
            return unvisited[0].node_id

        priors = self._compute_priors(active_nodes)
        total_visits = sum(n.visits for n in active_nodes)
        sqrt_total = math.sqrt(total_visits)

        best_node_id: Optional[str] = None
        best_score = float("-inf")
        for node in active_nodes:
            score = node.avg_value + self._c_puct * priors[node.node_id] * sqrt_total / (1 + node.visits)
            if score > best_score:
                best_score = score
                best_node_id = node.node_id
        return best_node_id

    def backpropagate(self, graph: ExplorationGraph, node_id: str, reward: float) -> None:
        """Backpropagate reward from leaf to all ancestors until root."""
        node_map = {n.node_id: n for n in graph.nodes}
        start = node_map.get(node_id)
        if start is None:
            return

        start.update_stats(reward)

        pending_parent_ids = list(start.parent_ids)
        seen: "set[str]" = set()

        while pending_parent_ids:
            parent_id = pending_parent_ids.pop()
            if parent_id in seen:
                continue

            parent = node_map.get(parent_id)
            if parent is None:
                continue

            parent.update_stats(reward)
            seen.add(parent_id)
            pending_parent_ids.extend(parent.parent_ids)

    def observe_feedback(
        self,
        graph: ExplorationGraph,
        node_id: str,
        score: Optional[float],
        decision: Optional[bool],
    ) -> None:
        """Convert feedback to reward and backpropagate."""
        reward = self._reward_calculator.calculate(score=score, decision=decision)
        self.backpropagate(graph, node_id, reward)

    def get_all_scores(self, graph: ExplorationGraph) -> Dict[str, float]:
        """Return PUCT score for every ACTIVE node."""
        active_nodes = [n for n in graph.nodes if n.branch_state == BranchState.ACTIVE]
        if not active_nodes:
            return {}

        priors = self._compute_priors(active_nodes)
        total_visits = sum(n.visits for n in active_nodes)
        sqrt_total = math.sqrt(total_visits)

        scores: Dict[str, float] = {}
        for node in active_nodes:
            if node.visits == 0:
                scores[node.node_id] = float("inf")
                continue

            puct = node.avg_value + self._c_puct * priors[node.node_id] * sqrt_total / (1 + node.visits)
            scores[node.node_id] = puct
        return scores

    @staticmethod
    def _compute_priors(active_nodes: "list[NodeRecord]") -> Dict[str, float]:
        """Compute softmax prior probability over node potentials."""
        potentials = {n.node_id: (n.score if n.score is not None else 0.0) for n in active_nodes}
        max_p = max(potentials.values())

        exp_values: Dict[str, float] = {}
        exp_sum = 0.0
        for node_id, potential in potentials.items():
            value = math.exp(potential - max_p)
            exp_values[node_id] = value
            exp_sum += value

        if exp_sum == 0.0:
            uniform = 1.0 / len(active_nodes)
            return {n.node_id: uniform for n in active_nodes}

        return {node_id: value / exp_sum for node_id, value in exp_values.items()}
