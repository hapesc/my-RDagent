"""Phase 28 holdout validation orchestration service."""

from __future__ import annotations

from uuid import uuid4

from v3.algorithms.holdout import collect_candidate_ids, filter_by_quality_threshold, rank_candidates
from v3.contracts.exploration import CandidateRankEntry, FinalSubmissionSnapshot
from v3.orchestration.dag_service import DAGService
from v3.ports.holdout_port import EvaluationPort, HoldoutSplitPort
from v3.ports.state_store import StateStorePort


class HoldoutValidationService:
    """Evaluate the final candidate pool with injected holdout split and scoring ports."""

    def __init__(
        self,
        *,
        state_store: StateStorePort,
        dag_service: DAGService,
        split_port: HoldoutSplitPort,
        evaluation_port: EvaluationPort,
    ) -> None:
        self._state_store = state_store
        self._dag_service = dag_service
        self._split_port = split_port
        self._evaluation_port = evaluation_port

    def finalize(self, *, run_id: str) -> FinalSubmissionSnapshot:
        all_nodes = self._dag_service.list_nodes(run_id)
        all_edges = self._state_store.list_dag_edges(run_id)
        frontier_ids = self._dag_service.get_frontier(run_id)
        candidate_ids = collect_candidate_ids(all_nodes, all_edges, frontier_ids)
        candidates = [node for node in all_nodes if node.node_id in candidate_ids]
        if not candidates:
            raise ValueError(f"no candidates found for run {run_id}")

        filtered_candidates = filter_by_quality_threshold(candidates)
        folds = self._split_port.split(run_id=run_id)
        if not folds:
            raise ValueError(f"split port returned no folds for run {run_id}")

        candidate_scores: dict[str, list[float]] = {}
        for candidate in filtered_candidates:
            candidate_scores[candidate.node_id] = [
                self._evaluation_port.evaluate(candidate_node_id=candidate.node_id, fold=fold)
                for fold in folds
            ]

        ranked_candidates = rank_candidates(candidate_scores)
        if not ranked_candidates:
            raise ValueError(f"no ranked candidates produced for run {run_id}")

        node_map = {node.node_id: node for node in all_nodes}
        for node_id, mean_score, std_score in ranked_candidates:
            node = node_map[node_id]
            updated_metrics = node.node_metrics.model_copy(
                update={"holdout_mean": mean_score, "holdout_std": std_score}
            )
            self._dag_service.update_node_metrics(node_id, updated_metrics)

        winner_id, winner_mean, winner_std = ranked_candidates[0]
        winner_node = node_map[winner_id]
        submission = FinalSubmissionSnapshot(
            submission_id=f"submission-{uuid4().hex[:12]}",
            run_id=run_id,
            winner_node_id=winner_id,
            winner_branch_id=winner_node.branch_id,
            holdout_mean=winner_mean,
            holdout_std=winner_std,
            ranked_candidates=[
                CandidateRankEntry(
                    node_id=node_id,
                    branch_id=node_map[node_id].branch_id,
                    rank=index + 1,
                    holdout_mean=mean_score,
                    holdout_std=std_score,
                )
                for index, (node_id, mean_score, std_score) in enumerate(ranked_candidates)
            ],
            ancestry_chain=sorted(self._dag_service.get_ancestors(winner_id, run_id)),
        )
        self._state_store.write_final_submission(submission)
        return submission


__all__ = ["HoldoutValidationService"]
