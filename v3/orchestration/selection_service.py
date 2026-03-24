"""V3-owned next-branch recommendation service."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from v3.contracts.branch import BranchStatus
from v3.contracts.exploration import BranchDecisionKind, BranchDecisionSnapshot, ExplorationMode
from v3.contracts.recovery import RecoveryDisposition
from v3.contracts.stage import StageKey
from v3.orchestration.puct_selection_adapter import PUCTBranchCandidate, PuctSelectionAdapter
from v3.orchestration.scoring_service import (
    BranchSelectionSignal,
    build_selection_rationale,
    project_branch_score,
    selection_potential,
)
from v3.ports.state_store import StateStorePort


@dataclass(frozen=True)
class BranchRecommendation:
    """Public recommendation result for the next branch to advance."""

    branch_id: str
    exploration_priority: float
    result_quality: float
    current_stage_key: StageKey
    recommended_next_step: str
    rationale: str


class SelectionService:
    """Selects the next branch through a V3 adapter over legacy PUCT math."""

    def __init__(
        self,
        state_store: StateStorePort,
        adapter: PuctSelectionAdapter | None = None,
    ) -> None:
        self._state_store = state_store
        self._adapter = adapter or PuctSelectionAdapter()

    def select_next_branch(self, *, run_id: str, include_completed: bool = False) -> BranchRecommendation:
        run = self._state_store.load_run_snapshot(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")

        eligible = []
        for branch_id in run.branch_ids:
            branch = self._state_store.load_branch_snapshot(branch_id)
            if branch is None:
                continue
            if not include_completed and branch.status is BranchStatus.COMPLETED:
                continue
            if branch.status not in {BranchStatus.ACTIVE, BranchStatus.CANDIDATE}:
                continue

            recovery = self._state_store.load_recovery_assessment(branch.branch_id, branch.current_stage_key)
            if recovery is None:
                continue
            if recovery.invalid_reasons or recovery.recovery_assessment == RecoveryDisposition.REBUILD:
                continue

            candidate = PUCTBranchCandidate(
                branch_id=branch.branch_id,
                potential=selection_potential(branch, recovery),
                avg_value=(branch.score.result_quality * 2.0) - 1.0,
                visits=max(1, round((1.0 - branch.score.exploration_priority) * 10)),
            )
            eligible.append((branch, recovery, candidate))

        if not eligible:
            raise ValueError("No eligible V3 branches available for recommendation.")

        selected_branch_id = self._adapter.select_next_branch([candidate for _, _, candidate in eligible])
        if selected_branch_id is None:
            raise ValueError("PUCT adapter did not select a branch.")

        try:
            branch, recovery, candidate = next(item for item in eligible if item[0].branch_id == selected_branch_id)
        except StopIteration:
            raise ValueError(f"Adapter returned unknown branch id: {selected_branch_id}")
        signal = BranchSelectionSignal(
            branch_id=branch.branch_id,
            branch_potential=candidate.potential,
            sibling_potentials=tuple(item[2].potential for item in eligible),
            avg_value=candidate.avg_value,
            visits=candidate.visits,
            total_visits=sum(item[2].visits for item in eligible),
        )
        projected_score = project_branch_score(signal)
        rationale = build_selection_rationale(branch, recovery, projected_score)
        decision = BranchDecisionSnapshot(
            decision_id=f"decision-select-{uuid4().hex[:12]}",
            run_id=run_id,
            branch_id=branch.branch_id,
            kind=BranchDecisionKind.SELECT,
            mode=ExplorationMode.EXPLORATION,
            summary=f"Selected {branch.label} via the V3 PUCT adapter.",
            rationale=rationale,
            resolution=branch.resolution,
            affected_branch_ids=[branch.branch_id],
        )
        self._state_store.write_branch_decision(decision)
        self._state_store.write_run_snapshot(
            run.model_copy(
                update={
                    "exploration_mode": ExplorationMode.EXPLORATION,
                    "latest_branch_decision_id": decision.decision_id,
                }
            )
        )
        return BranchRecommendation(
            branch_id=branch.branch_id,
            exploration_priority=projected_score.exploration_priority,
            result_quality=projected_score.result_quality,
            current_stage_key=branch.current_stage_key,
            recommended_next_step=recovery.recommended_next_step,
            rationale=rationale,
        )


__all__ = ["BranchRecommendation", "SelectionService"]
