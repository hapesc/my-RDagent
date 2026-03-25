"""Phase 16 merge and fallback orchestration."""

from __future__ import annotations

from uuid import uuid4

from rd_agent.algorithms.complementarity import component_coverage_distance
from rd_agent.algorithms.merge import MergeAdapter
from rd_agent.contracts.exploration import (
    BranchDecisionKind,
    BranchDecisionSnapshot,
    EdgeType,
    ExplorationMode,
    MergeOutcomeSnapshot,
    NodeMetrics,
)
from rd_agent.contracts.tool_io import (
    BranchFallbackRequest,
    BranchFallbackResult,
    BranchMergeRequest,
    BranchMergeResult,
    BranchShortlistRequest,
)
from rd_agent.orchestration.branch_board_service import BranchBoardService
from rd_agent.orchestration.convergence_service import ConvergenceService
from rd_agent.orchestration.dag_service import DAGService
from rd_agent.ports.state_store import StateStorePort


class BranchMergeService:
    """Executes merge attempts and top-1 fallback over shortlist state."""

    def __init__(
        self,
        state_store: StateStorePort,
        convergence_service: ConvergenceService,
        board_service: BranchBoardService | None = None,
        merger: MergeAdapter | None = None,
        dag_service: DAGService | None = None,
    ) -> None:
        self._state_store = state_store
        self._convergence_service = convergence_service
        self._board_service = board_service or BranchBoardService(state_store)
        self._merger = merger
        self._dag_service = dag_service

    def merge(self, request: BranchMergeRequest) -> BranchMergeResult:
        shortlist_result = self._convergence_service.shortlist(
            BranchShortlistRequest(run_id=request.run_id, minimum_quality=request.minimum_quality)
        )
        shortlist = shortlist_result.shortlist
        if len(shortlist) < 2:
            outcome = MergeOutcomeSnapshot(
                outcome_id=f"merge-outcome-{uuid4().hex[:12]}",
                run_id=request.run_id,
                summary="Merge declined because convergence quality was insufficient (insufficient_shortlist).",
                rationale="At least two high-quality branches are required before merge judgment.",
                failure_reason="insufficient_shortlist",
                shortlist=shortlist,
            )
            self._persist_merge_decision(request.run_id, outcome)
            return BranchMergeResult(outcome=outcome, board=self._board_service.get_board(request.run_id))

        lead = shortlist[0]
        runner_up = shortlist[1]
        lead_branch = self._state_store.load_branch_snapshot(lead.branch_id)
        runner_branch = self._state_store.load_branch_snapshot(runner_up.branch_id)
        assert lead_branch is not None and runner_branch is not None

        if lead_branch.score.result_quality - runner_branch.score.result_quality > 0.15:
            outcome = MergeOutcomeSnapshot(
                outcome_id=f"merge-outcome-{uuid4().hex[:12]}",
                run_id=request.run_id,
                summary="Merge quality degraded below the convergence threshold (quality_gap_too_wide).",
                rationale="The shortlist spread was too wide to justify synthesis.",
                failure_reason="quality_gap_too_wide",
                shortlist=shortlist,
            )
            self._persist_merge_decision(request.run_id, outcome)
            return BranchMergeResult(outcome=outcome, board=self._board_service.get_board(request.run_id))

        synthesis = f"Synthesis of {lead.branch_id} and {runner_up.branch_id}."
        if self._merger is not None:
            synthesis = self._merger.merge(
                traces=[
                    {"design": {"summary": lead.rationale}},
                    {"design": {"summary": runner_up.rationale}},
                ],
                task_summary=shortlist_result.candidate_summary.conclusions[0],
                scenario_name="phase16-convergence",
            ).summary
        outcome = MergeOutcomeSnapshot(
            outcome_id=f"merge-outcome-{uuid4().hex[:12]}",
            run_id=request.run_id,
            summary=synthesis,
            rationale="Candidate summary and shortlist passed the merge gate.",
            merged_branch_id=lead.branch_id,
            source_branch_ids=[lead.branch_id, runner_up.branch_id],
            shortlist=shortlist,
        )
        self._persist_merge_decision(request.run_id, outcome)
        return BranchMergeResult(outcome=outcome, board=self._board_service.get_board(request.run_id))

    def merge_with_complementarity(
        self,
        request: BranchMergeRequest,
        branch_component_scores: dict[str, dict[str, float]],
    ) -> BranchMergeResult:
        """Select merge sources by component complementarity and gate the result by holdout."""

        shortlist_result = self._convergence_service.shortlist(
            BranchShortlistRequest(run_id=request.run_id, minimum_quality=request.minimum_quality)
        )
        shortlist = shortlist_result.shortlist
        if len(shortlist) < 2:
            return self.merge(request)

        best_pair: tuple[str, str] | None = None
        best_distance = -1.0
        for index, entry_a in enumerate(shortlist):
            for entry_b in shortlist[index + 1 :]:
                distance = component_coverage_distance(
                    branch_component_scores.get(entry_a.branch_id, {}),
                    branch_component_scores.get(entry_b.branch_id, {}),
                )
                if distance > best_distance:
                    best_distance = distance
                    best_pair = (entry_a.branch_id, entry_b.branch_id)

        if best_pair is None:
            return self.merge(request)

        lead_id, partner_id = best_pair
        lead_branch = self._state_store.load_branch_snapshot(lead_id)
        partner_branch = self._state_store.load_branch_snapshot(partner_id)
        if lead_branch is None or partner_branch is None:
            return self.merge(request)

        lead_components = {name: score for name, score in branch_component_scores.get(lead_id, {}).items() if score >= 0.4}
        partner_components = {
            name: score for name, score in branch_component_scores.get(partner_id, {}).items() if score >= 0.4
        }
        for component_name in set(lead_components) & set(partner_components):
            if lead_components[component_name] < partner_components[component_name]:
                lead_components.pop(component_name, None)
            else:
                partner_components.pop(component_name, None)

        synthesis = f"Complementary merge of {lead_id} and {partner_id}."
        merge_design = None
        if self._merger is not None:
            merge_design = self._merger.merge(
                traces=[
                    {
                        "branch_id": lead_id,
                        "design": {"summary": lead_branch.label},
                        "components": lead_components,
                    },
                    {
                        "branch_id": partner_id,
                        "design": {"summary": partner_branch.label},
                        "components": partner_components,
                    },
                ],
                task_summary=shortlist_result.candidate_summary.conclusions[0]
                if shortlist_result.candidate_summary.conclusions
                else "merge",
                scenario_name="phase27-complementary-merge",
            )
            synthesis = merge_design.summary

        best_single_score = max(
            (
                branch.score.result_quality
                for entry in shortlist
                if (branch := self._state_store.load_branch_snapshot(entry.branch_id)) is not None
            ),
            default=0.0,
        )
        holdout_score = (
            merge_design.holdout_score
            if merge_design is not None and merge_design.holdout_score is not None
            else best_single_score + best_distance * 0.1
        )
        if not (holdout_score >= best_single_score):
            outcome = MergeOutcomeSnapshot(
                outcome_id=f"merge-outcome-{uuid4().hex[:12]}",
                run_id=request.run_id,
                summary="Merged candidate did not outperform the best single branch on holdout.",
                rationale=f"holdout_score={holdout_score:.4f} < best_single={best_single_score:.4f}",
                failure_reason="holdout_validation_failed",
                shortlist=shortlist,
            )
            self._persist_merge_decision(request.run_id, outcome)
            return BranchMergeResult(outcome=outcome, board=self._board_service.get_board(request.run_id))

        if self._dag_service is not None:
            merged_node = self._dag_service.create_node(
                run_id=request.run_id,
                branch_id=lead_id,
                node_metrics=NodeMetrics(
                    validation_score=min(1.0, holdout_score),
                    complementarity_score=best_distance,
                ),
            )
            all_nodes = self._dag_service.list_nodes(request.run_id)
            for source_branch_id in (lead_id, partner_id):
                source_nodes = [node for node in all_nodes if node.branch_id == source_branch_id]
                if not source_nodes:
                    continue
                latest = max(source_nodes, key=lambda node: node.depth)
                self._dag_service.create_typed_edge(
                    source_node_id=latest.node_id,
                    target_node_id=merged_node.node_id,
                    edge_type=EdgeType.MERGED,
                )

        outcome = MergeOutcomeSnapshot(
            outcome_id=f"merge-outcome-{uuid4().hex[:12]}",
            run_id=request.run_id,
            summary=synthesis,
            rationale=f"Complementary merge with coverage distance {best_distance:.2f}.",
            merged_branch_id=lead_id,
            source_branch_ids=[lead_id, partner_id],
            shortlist=shortlist,
        )
        self._persist_merge_decision(request.run_id, outcome)
        return BranchMergeResult(outcome=outcome, board=self._board_service.get_board(request.run_id))

    def fallback(self, request: BranchFallbackRequest) -> BranchFallbackResult:
        shortlist_result = self._convergence_service.shortlist(
            BranchShortlistRequest(run_id=request.run_id, minimum_quality=request.minimum_quality)
        )
        if not shortlist_result.shortlist:
            raise ValueError("no shortlist candidates available for fallback")
        top = shortlist_result.shortlist[0]
        return BranchFallbackResult(
            selected_branch_id=top.branch_id,
            rationale="Fallback selected the top-ranked branch from the quality-ordered shortlist.",
            shortlist=shortlist_result.shortlist,
        )

    def _persist_merge_decision(self, run_id: str, outcome: MergeOutcomeSnapshot) -> None:
        branch_id = outcome.merged_branch_id or (outcome.shortlist[0].branch_id if outcome.shortlist else "run-wide")
        decision = BranchDecisionSnapshot(
            decision_id=f"decision-merge-{uuid4().hex[:12]}",
            run_id=run_id,
            branch_id=branch_id,
            kind=BranchDecisionKind.MERGE,
            mode=ExplorationMode.CONVERGENCE,
            summary=outcome.summary
            if outcome.failure_reason is None
            else f"{outcome.summary} Failure: {outcome.failure_reason}.",
            rationale=outcome.rationale,
            affected_branch_ids=[entry.branch_id for entry in outcome.shortlist]
            or ([branch_id] if branch_id != "run-wide" else []),
        )
        self._state_store.write_branch_decision(decision)
        run = self._state_store.load_run_snapshot(run_id)
        if run is not None:
            self._state_store.write_run_snapshot(
                run.model_copy(
                    update={
                        "exploration_mode": ExplorationMode.CONVERGENCE,
                        "latest_branch_decision_id": decision.decision_id,
                        "latest_merge_outcome_id": outcome.outcome_id,
                    }
                )
            )


__all__ = ["BranchMergeService"]
