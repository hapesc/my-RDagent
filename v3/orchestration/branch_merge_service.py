"""Phase 16 merge and fallback orchestration."""

from __future__ import annotations

from uuid import uuid4

from v3.algorithms.merge import MergeAdapter
from v3.contracts.exploration import BranchDecisionKind, BranchDecisionSnapshot, ExplorationMode, MergeOutcomeSnapshot
from v3.contracts.tool_io import (
    BranchFallbackRequest,
    BranchFallbackResult,
    BranchMergeRequest,
    BranchMergeResult,
    BranchShortlistRequest,
)
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.convergence_service import ConvergenceService
from v3.ports.state_store import StateStorePort


class BranchMergeService:
    """Executes merge attempts and top-1 fallback over shortlist state."""

    def __init__(
        self,
        state_store: StateStorePort,
        convergence_service: ConvergenceService,
        board_service: BranchBoardService | None = None,
        merger: MergeAdapter | None = None,
    ) -> None:
        self._state_store = state_store
        self._convergence_service = convergence_service
        self._board_service = board_service or BranchBoardService(state_store)
        self._merger = merger

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
            summary=outcome.summary if outcome.failure_reason is None else f"{outcome.summary} Failure: {outcome.failure_reason}.",
            rationale=outcome.rationale,
            affected_branch_ids=[entry.branch_id for entry in outcome.shortlist] or ([branch_id] if branch_id != "run-wide" else []),
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
