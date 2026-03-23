"""Phase 26 parent-node selection over DAG topology."""

from __future__ import annotations

from dataclasses import dataclass

from v3.algorithms.decay import cosine_decay
from v3.contracts.exploration import DAGNodeSnapshot
from v3.orchestration.dag_service import DAGService
from v3.ports.state_store import StateStorePort


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
        else:
            k = 1

        branch_nodes = [node for node in self._dag_service.list_nodes(run_id) if node.branch_id == branch_id]
        if not branch_nodes:
            raise KeyError(f"no DAG nodes for branch {branch_id} in run {run_id}")

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
            quality = (
                metrics.validation_score
                * (1.0 - metrics.overfitting_risk)
                * (1.0 - min(1.0, metrics.generalization_gap))
            )
            combined = quality * (1.0 - diversity_weight) + metrics.diversity_score * diversity_weight
            scored.append((node.node_id, combined))
        return scored


__all__ = ["ParentRecommendation", "SelectParentsService"]
