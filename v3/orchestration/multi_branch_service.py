"""High-level Phase 16 coordinator above the single-branch skill loop."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from v3.contracts.tool_io import ConvergeRoundRequest, ConvergeRoundResult, ExploreRoundRequest, ExploreRoundResult
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_lifecycle_service import BranchLifecycleService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.selection_service import SelectionService
from v3.ports.state_store import StateStorePort


DispatchFn = Callable[[dict[str, Any]], dict[str, Any]]


class MultiBranchService:
    """Coordinates multi-branch exploration rounds without teaching SkillLoopService frontier state."""

    def __init__(
        self,
        *,
        state_store: StateStorePort,
        workspace_manager: BranchWorkspaceManager,
        branch_lifecycle_service: BranchLifecycleService,
        branch_board_service: BranchBoardService,
        selection_service: SelectionService,
        branch_merge_service: BranchMergeService,
        dispatcher: DispatchFn | None = None,
    ) -> None:
        self._state_store = state_store
        self._workspace_manager = workspace_manager
        self._branch_lifecycle_service = branch_lifecycle_service
        self._branch_board_service = branch_board_service
        self._selection_service = selection_service
        self._branch_merge_service = branch_merge_service
        self._dispatcher = dispatcher or (lambda payload: {"status": "queued", **payload})

    def run_exploration_round(self, request: ExploreRoundRequest) -> ExploreRoundResult:
        run = self._state_store.load_run_snapshot(request.run_id)
        if run is None:
            raise KeyError(f"run not found: {request.run_id}")
        primary_branch = self._state_store.load_branch_snapshot(run.primary_branch_id) if run.primary_branch_id else None
        if primary_branch is None:
            raise KeyError("primary branch missing for exploration round")

        by_label = {primary_branch.label: primary_branch}
        dispatched_branch_ids: list[str] = []
        for hypothesis in request.hypotheses:
            branch = by_label.get(hypothesis)
            if branch is None:
                publication = self._branch_lifecycle_service.fork_branch(
                    __import__("v3.contracts.tool_io", fromlist=["BranchForkRequest"]).BranchForkRequest(
                        run_id=request.run_id,
                        source_branch_id=primary_branch.branch_id,
                        label=hypothesis,
                        rationale=f"Fork branch for hypothesis {hypothesis}.",
                    )
                )
                branch = publication.branch
                by_label[hypothesis] = branch
            workspace_root = self._workspace_manager.workspace_root(run_id=request.run_id, branch_id=branch.branch_id)
            if not Path(workspace_root).exists():
                workspace_root = self._workspace_manager.allocate_branch_workspace(
                    run_id=request.run_id,
                    branch_id=branch.branch_id,
                )
            self._dispatcher(
                {
                    "run_id": request.run_id,
                    "branch_id": branch.branch_id,
                    "label": branch.label,
                    "workspace_root": workspace_root,
                }
            )
            dispatched_branch_ids.append(branch.branch_id)

        board = self._branch_board_service.get_board(request.run_id)
        try:
            recommendation = self._selection_service.select_next_branch(run_id=request.run_id, include_completed=True)
            selected_branch_id = recommendation.branch_id
            recommended_next_step = recommendation.recommended_next_step
            rationale = recommendation.rationale
        except Exception:
            selected_branch_id = board.active_cards[0].branch_id
            recommended_next_step = "continue explore round"
            rationale = "No recovery-backed recommendation yet; continue exploring active branches."
        return ExploreRoundResult(
            selected_branch_id=selected_branch_id,
            recommended_next_step=recommended_next_step,
            rationale=rationale,
            board=board,
            dispatched_branch_ids=dispatched_branch_ids,
        )

    def run_convergence_round(self, request: ConvergeRoundRequest) -> ConvergeRoundResult:
        merge_result = self._branch_merge_service.merge(
            __import__("v3.contracts.tool_io", fromlist=["BranchMergeRequest"]).BranchMergeRequest(
                run_id=request.run_id,
                minimum_quality=request.minimum_quality,
            )
        )
        if merge_result.outcome.failure_reason is None and merge_result.outcome.merged_branch_id is not None:
            return ConvergeRoundResult(
                selected_branch_id=merge_result.outcome.merged_branch_id,
                recommended_next_step="review merged synthesis",
                rationale="Convergence merged the leading shortlist entries.",
                board=merge_result.board,
                merge_summary=merge_result.outcome.summary,
            )
        try:
            fallback = self._branch_merge_service.fallback(
                __import__("v3.contracts.tool_io", fromlist=["BranchFallbackRequest"]).BranchFallbackRequest(
                    run_id=request.run_id,
                    minimum_quality=request.minimum_quality,
                )
            )
            selected_branch_id = fallback.selected_branch_id
            rationale = fallback.rationale
        except ValueError:
            board = self._branch_board_service.get_board(request.run_id)
            if not board.active_cards:
                raise
            selected_branch_id = board.active_cards[0].branch_id
            rationale = "No shortlist met the convergence threshold; continue with the top active branch."
        return ConvergeRoundResult(
            selected_branch_id=selected_branch_id,
            recommended_next_step="continue with top-ranked branch",
            rationale=rationale,
            board=merge_result.board,
            merge_summary=merge_result.outcome.summary,
        )


__all__ = ["MultiBranchService"]
