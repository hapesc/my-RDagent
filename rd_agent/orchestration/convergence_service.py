"""Phase 16 candidate summary and shortlist construction."""

from __future__ import annotations

from uuid import uuid4

from rd_agent.contracts.exploration import CandidateSummarySnapshot, ShortlistEntrySnapshot
from rd_agent.contracts.tool_io import BranchShortlistRequest, BranchShortlistResult
from rd_agent.orchestration.branch_board_service import BranchBoardService
from rd_agent.ports.state_store import StateStorePort


class ConvergenceService:
    """Builds candidate summaries and quality-ordered shortlists."""

    def __init__(
        self,
        state_store: StateStorePort,
        board_service: BranchBoardService | None = None,
    ) -> None:
        self._state_store = state_store
        self._board_service = board_service or BranchBoardService(state_store)

    def shortlist(self, request: BranchShortlistRequest) -> BranchShortlistResult:
        board = self._board_service.get_board(request.run_id)
        ranked = []
        for card in board.active_cards:
            branch = self._state_store.load_branch_snapshot(card.branch_id)
            if branch is None:
                continue
            ranked.append(branch)
        ranked.sort(
            key=lambda branch: (-branch.score.result_quality, -branch.score.exploration_priority, branch.branch_id)
        )
        shortlist = [
            ShortlistEntrySnapshot(
                branch_id=branch.branch_id,
                rank=index + 1,
                rationale=f"{branch.label} kept with quality {branch.score.result_quality:.2f}.",
            )
            for index, branch in enumerate(ranked)
            if branch.score.result_quality >= request.minimum_quality
        ]
        candidate_summary = CandidateSummarySnapshot(
            summary_id=f"candidate-summary-{uuid4().hex[:12]}",
            run_id=request.run_id,
            branch_ids=[branch.branch_id for branch in ranked],
            conclusions=[f"{branch.label}: {branch.score.rationale}" for branch in ranked[:3]],
            evidence=[branch.lineage.source_summary or branch.label for branch in ranked[:3]],
            hypothesis_evolution=[branch.label for branch in ranked[:3]],
        )
        return BranchShortlistResult(candidate_summary=candidate_summary, shortlist=shortlist, board=board)


__all__ = ["ConvergenceService"]
