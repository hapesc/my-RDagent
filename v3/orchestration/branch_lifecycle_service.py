"""Phase 16 branch fork lifecycle over canonical V3 state and workspace seams."""

from __future__ import annotations

from uuid import uuid4

from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import (
    BranchDecisionKind,
    BranchDecisionSnapshot,
    ExplorationMode,
)
from v3.contracts.stage import StageKey
from v3.contracts.tool_io import BranchForkRequest, BranchForkResult
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.run_board_service import RunBoardService
from v3.ports.state_store import StateStorePort


class BranchLifecycleService:
    """Creates globally unique branch forks without breaking branch isolation."""

    def __init__(
        self,
        *,
        state_store: StateStorePort,
        workspace_manager: BranchWorkspaceManager,
        run_board_service: RunBoardService,
    ) -> None:
        self._state_store = state_store
        self._workspace_manager = workspace_manager
        self._run_board_service = run_board_service

    def fork_branch(self, request: BranchForkRequest) -> BranchForkResult:
        run = self._state_store.load_run_snapshot(request.run_id)
        if run is None:
            raise KeyError(f"run not found: {request.run_id}")

        label = request.label.strip()
        if not label:
            raise ValueError("label must not be empty")

        rationale = request.rationale.strip()
        if not rationale:
            raise ValueError("rationale must not be empty")

        source_branch = None
        source_workspace_root = None
        source_branch_id = request.source_branch_id
        if source_branch_id is not None:
            source_branch = self._state_store.load_branch_snapshot(source_branch_id)
            if source_branch is None:
                raise KeyError(f"branch not found: {source_branch_id}")
            if source_branch.run_id != request.run_id:
                raise ValueError("source_branch_id must belong to the requested run")
            source_workspace_root = self._workspace_manager.workspace_root(
                run_id=request.run_id,
                branch_id=source_branch_id,
            )

        branch_id = f"branch-{uuid4().hex[:12]}"
        decision_id = f"decision-{uuid4().hex[:12]}"
        workspace_root = self._workspace_manager.allocate_branch_workspace(
            run_id=request.run_id,
            branch_id=branch_id,
            source_path=source_workspace_root,
        )

        source_summary = rationale
        if source_branch is not None:
            source_summary = f"Forked from {source_branch.label}: {rationale}"

        branch = BranchSnapshot(
            branch_id=branch_id,
            run_id=request.run_id,
            label=label,
            status=BranchStatus.ACTIVE,
            current_stage_key=self._stage_key_for_new_branch(run.primary_branch_id, source_branch),
            stages=list(source_branch.stages) if source_branch is not None else [],
            score=source_branch.score
            if source_branch is not None
            else BranchScore(
                exploration_priority=0.5,
                result_quality=0.0,
                rationale=f"{label} is a newly forked hypothesis awaiting evidence.",
            ),
            lineage=BranchLineage(
                parent_branch_id=source_branch_id,
                source_summary=source_summary,
            ),
            artifact_ids=list(source_branch.artifact_ids) if source_branch is not None else [],
        )

        if source_branch is not None:
            updated_source = source_branch.model_copy(
                update={
                    "lineage": source_branch.lineage.model_copy(
                        update={
                            "child_branch_ids": [*source_branch.lineage.child_branch_ids, branch_id],
                        }
                    )
                }
            )
            self._state_store.write_branch_snapshot(updated_source)

        decision = BranchDecisionSnapshot(
            decision_id=decision_id,
            run_id=request.run_id,
            branch_id=branch_id,
            kind=BranchDecisionKind.FORK,
            mode=ExplorationMode.EXPLORATION,
            summary=f"Forked branch {label}.",
            rationale=rationale,
            source_branch_id=source_branch_id,
            affected_branch_ids=[item for item in [source_branch_id, branch_id] if item is not None],
        )
        self._state_store.write_branch_decision(decision)
        self._run_board_service.append_branch(
            run_id=request.run_id,
            branch=branch,
            latest_branch_decision_id=decision_id,
            exploration_mode=ExplorationMode.EXPLORATION,
        )

        return BranchForkResult(branch=branch, decision=decision, workspace_root=workspace_root)

    def _stage_key_for_new_branch(
        self,
        primary_branch_id: str | None,
        source_branch: BranchSnapshot | None,
    ) -> StageKey:
        if source_branch is not None:
            return source_branch.current_stage_key
        if primary_branch_id is None:
            return StageKey.FRAMING
        primary_branch = self._state_store.load_branch_snapshot(primary_branch_id)
        if primary_branch is None:
            return StageKey.FRAMING
        return primary_branch.current_stage_key


__all__ = ["BranchLifecycleService"]
