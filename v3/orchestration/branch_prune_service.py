"""Phase 26 pruning service over the multi-signal V3 cutoff algorithm."""

from __future__ import annotations

from uuid import uuid4

from v3.algorithms.prune import prune_branch_candidates
from v3.contracts.branch import BranchStatus
from v3.contracts.exploration import BranchDecisionKind, BranchDecisionSnapshot, BranchResolution, ExplorationMode
from v3.contracts.tool_io import BranchPruneRequest, BranchPruneResult
from v3.orchestration.branch_board_service import BranchBoardService
from v3.ports.state_store import StateStorePort


class BranchPruneService:
    """Prunes weak branches while preserving explicit V3 decision state."""

    def __init__(
        self,
        state_store: StateStorePort,
        board_service: BranchBoardService | None = None,
    ) -> None:
        self._state_store = state_store
        self._board_service = board_service or BranchBoardService(state_store)

    def prune(self, request: BranchPruneRequest) -> BranchPruneResult:
        run = self._state_store.load_run_snapshot(request.run_id)
        if run is None:
            raise KeyError(f"run not found: {request.run_id}")

        active_branches = [
            branch
            for branch_id in run.branch_ids
            if (branch := self._state_store.load_branch_snapshot(branch_id)) is not None
            and branch.status in {BranchStatus.ACTIVE, BranchStatus.CANDIDATE}
        ]
        use_multi_signal = run.exploration_mode is ExplorationMode.EXPLORATION
        budget_ratio = run.current_round / max(run.max_rounds, 1) if use_multi_signal else None
        generalization_gaps = (
            {branch.branch_id: branch.score.generalization_gap for branch in active_branches}
            if use_multi_signal
            else None
        )
        overfitting_risks = (
            {branch.branch_id: branch.score.overfitting_risk for branch in active_branches}
            if use_multi_signal
            else None
        )
        min_active_branches = request.min_active_branches if use_multi_signal else 1
        pruned_branch_ids = prune_branch_candidates(
            [(branch.branch_id, branch.score.result_quality) for branch in active_branches],
            relative_threshold=request.relative_threshold,
            budget_ratio=budget_ratio,
            generalization_gaps=generalization_gaps,
            overfitting_risks=overfitting_risks,
            min_active_branches=min_active_branches,
        )
        decision_ids: list[str] = []
        for branch_id in pruned_branch_ids:
            branch = self._state_store.load_branch_snapshot(branch_id)
            if branch is None:
                continue
            updated_branch = branch.model_copy(
                update={
                    "status": BranchStatus.SUPERSEDED,
                    "resolution": BranchResolution.PRUNED,
                }
            )
            self._state_store.write_branch_snapshot(updated_branch)
            decision = BranchDecisionSnapshot(
                decision_id=f"decision-prune-{uuid4().hex[:12]}",
                run_id=request.run_id,
                branch_id=branch_id,
                kind=BranchDecisionKind.PRUNE,
                mode=ExplorationMode.EXPLORATION,
                summary=f"Pruned {branch.label} after falling below the multi-signal frontier cutoff.",
                rationale=(
                    f"Pruned {branch.label} via multi-signal criteria at budget_ratio={budget_ratio:.2f} "
                    f"while preserving at least {min_active_branches} active branch(es)."
                    if use_multi_signal and budget_ratio is not None
                    else "The branch fell below the V3 prune threshold while keeping at least one active branch."
                ),
                resolution=BranchResolution.PRUNED,
                affected_branch_ids=[branch_id],
            )
            self._state_store.write_branch_decision(decision)
            decision_ids.append(decision.decision_id)

        updated_run = run.model_copy(
            update={
                "exploration_mode": ExplorationMode.EXPLORATION,
                "latest_branch_decision_id": decision_ids[-1] if decision_ids else run.latest_branch_decision_id,
            }
        )
        self._state_store.write_run_snapshot(updated_run)
        board = self._board_service.get_board(request.run_id)
        active_branch_ids = [card.branch_id for card in board.active_cards]
        return BranchPruneResult(
            run_id=request.run_id,
            active_branch_ids=active_branch_ids,
            pruned_branch_ids=pruned_branch_ids,
            decision_ids=decision_ids,
            board=board,
        )


__all__ = ["BranchPruneService"]
