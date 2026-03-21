"""Phase 16 board read-model projection over canonical run and branch state."""

from __future__ import annotations

from v3.contracts.branch import BranchSnapshot, BranchStatus
from v3.contracts.exploration import (
    BranchBoardSnapshot,
    BranchCardSnapshot,
    BranchDecisionKind,
    BranchDecisionSnapshot,
    BranchResolution,
    ExplorationMode,
)
from v3.ports.state_store import StateStorePort


class BranchBoardService:
    """Projects branch cards into active and history board groupings."""

    def __init__(self, state_store: StateStorePort) -> None:
        self._state_store = state_store

    def get_board(self, run_id: str) -> BranchBoardSnapshot:
        run = self._state_store.load_run_snapshot(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")

        decisions = self._state_store.list_branch_decisions(run_id)
        latest_by_branch = self._latest_decisions(decisions)
        cards = [
            self._card_for_branch(branch, latest_by_branch.get(branch.branch_id))
            for branch_id in run.branch_ids
            if (branch := self._state_store.load_branch_snapshot(branch_id)) is not None
        ]

        active_cards = [card for card in cards if not self._is_history_card(card)]
        history_cards = [card for card in cards if self._is_history_card(card)]
        board = BranchBoardSnapshot(
            board_id=f"branch-board:{run_id}",
            run_id=run_id,
            mode=run.exploration_mode or ExplorationMode.EXPLORATION,
            active_cards=active_cards,
            history_cards=history_cards,
            summary=f"{len(active_cards)} active branch(es); {len(history_cards)} historical branch(es).",
        )
        self._state_store.write_branch_board_snapshot(board)
        return board

    def _card_for_branch(
        self,
        branch: BranchSnapshot,
        decision: BranchDecisionSnapshot | None,
    ) -> BranchCardSnapshot:
        explanation = branch.score.rationale
        shared_from_branch_ids: list[str] = []
        latest_decision_kind = None
        latest_decision_id = None
        if decision is not None:
            latest_decision_kind = decision.kind
            latest_decision_id = decision.decision_id
            explanation = self.share_explanation(decision)
            if decision.kind is BranchDecisionKind.SHARE and decision.source_branch_id is not None:
                shared_from_branch_ids = [decision.source_branch_id]

        return BranchCardSnapshot(
            branch_id=branch.branch_id,
            label=branch.label,
            status=branch.status.value,
            resolution=branch.resolution,
            current_stage_key=branch.current_stage_key,
            explanation=explanation,
            latest_decision_kind=latest_decision_kind,
            latest_decision_id=latest_decision_id,
            shared_from_branch_ids=shared_from_branch_ids,
        )

    def _latest_decisions(
        self,
        decisions: list[BranchDecisionSnapshot],
    ) -> dict[str, BranchDecisionSnapshot]:
        latest: dict[str, BranchDecisionSnapshot] = {}
        for decision in decisions:
            latest[decision.branch_id] = decision
        return latest

    def _is_history_card(self, card: BranchCardSnapshot) -> bool:
        return card.status in {BranchStatus.COMPLETED.value, BranchStatus.SUPERSEDED.value} or card.resolution in {
            BranchResolution.MERGED,
            BranchResolution.PRUNED,
            BranchResolution.REJECTED,
        }

    def share_explanation(self, decision: BranchDecisionSnapshot) -> str:
        if decision.kind is not BranchDecisionKind.SHARE:
            return decision.summary
        if decision.source_branch_id is None:
            return decision.summary
        return f"{decision.summary} Shared from {decision.source_branch_id}."


__all__ = ["BranchBoardService"]
