"""Phase 26 parent-node selection over DAG topology."""

from __future__ import annotations

from dataclasses import dataclass

from rd_agent.algorithms.complementarity import complementarity_score
from rd_agent.algorithms.decay import cosine_decay
from rd_agent.contracts.exploration import DAGNodeSnapshot, NodeMetrics
from rd_agent.orchestration.dag_service import DAGService
from rd_agent.ports.state_store import StateStorePort


@dataclass(frozen=True)
class ParentRecommendation:
    """Selected parent node IDs and the policy context used to choose them."""

    parent_node_ids: list[str]
    rationale: str
    budget_ratio: float
    diversity_weight: float


class SelectParentsService:
    """Selects parent nodes for the next iteration of a branch."""

    def __init__(self, state_store: StateStorePort, dag_service: DAGService) -> None:
        self._state_store = state_store
        self._dag_service = dag_service

    def select_parents(
        self,
        *,
        run_id: str,
        branch_id: str,
        max_parents: int | None = None,
    ) -> ParentRecommendation:
        run = self._state_store.load_run_snapshot(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")

        budget_ratio = run.current_round / max(run.max_rounds, 1)
        diversity_weight = cosine_decay(budget_ratio)
        if max_parents is not None:
            k = max(1, max_parents)
        elif budget_ratio < 0.3:
            k = 3
        elif budget_ratio >= 0.8:
            k = 2
        else:
            k = 1

        branch_nodes = [node for node in self._dag_service.list_nodes(run_id) if node.branch_id == branch_id]
        if not branch_nodes:
            raise KeyError(f"no DAG nodes for branch {branch_id} in run {run_id}")

        if budget_ratio >= 0.8 and k >= 2:
            quality_scored = [(node.node_id, self._quality_score(node.node_metrics)) for node in branch_nodes]
            quality_scored.sort(key=lambda item: item[1], reverse=True)
            first_id = quality_scored[0][0] if quality_scored else None
            if first_id is None:
                selected = []
            else:
                first_node = next(node for node in branch_nodes if node.node_id == first_id)
                complementarity_scored = self._score_candidates_with_complementarity(
                    branch_nodes,
                    diversity_weight,
                    first_parent_node=first_node,
                )
                complementarity_scored.sort(key=lambda item: item[1], reverse=True)
                selected = [first_id] + [node_id for node_id, _score in complementarity_scored[: k - 1]]
        else:
            scored = self._score_candidates(branch_nodes, diversity_weight)
            scored.sort(key=lambda item: item[1], reverse=True)
            selected = [node_id for node_id, _score in scored[:k]]
        phase = "early" if budget_ratio < 0.3 else "iteration" if budget_ratio < 0.8 else "merge"
        rationale = (
            f"Selected {len(selected)} parent(s) for {branch_id} at budget_ratio={budget_ratio:.2f} "
            f"with diversity_weight={diversity_weight:.2f} during the {phase} phase."
        )
        return ParentRecommendation(
            parent_node_ids=selected,
            rationale=rationale,
            budget_ratio=budget_ratio,
            diversity_weight=diversity_weight,
        )

    def _score_candidates(
        self,
        nodes: list[DAGNodeSnapshot],
        diversity_weight: float,
    ) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for node in nodes:
            metrics = node.node_metrics
            quality = self._quality_score(metrics)
            combined = quality * (1.0 - diversity_weight) + metrics.diversity_score * diversity_weight
            scored.append((node.node_id, combined))
        return scored

    def _score_candidates_with_complementarity(
        self,
        nodes: list[DAGNodeSnapshot],
        diversity_weight: float,
        *,
        first_parent_node: DAGNodeSnapshot,
    ) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        first_metrics = first_parent_node.node_metrics
        for node in nodes:
            if node.node_id == first_parent_node.node_id:
                continue
            metrics = node.node_metrics
            quality = self._quality_score(metrics)
            coverage_dist = abs(metrics.complementarity_score - first_metrics.complementarity_score)
            semantic_dist = abs(metrics.diversity_score - first_metrics.diversity_score)
            comp = complementarity_score(coverage_dist, semantic_dist)
            combined = quality * 0.4 + comp * 0.6
            scored.append((node.node_id, combined))
        return scored

    def _quality_score(self, metrics: NodeMetrics) -> float:
        return (
            metrics.validation_score
            * (1.0 - metrics.overfitting_risk)
            * (1.0 - min(1.0, metrics.generalization_gap))
        )


__all__ = ["ParentRecommendation", "SelectParentsService"]
