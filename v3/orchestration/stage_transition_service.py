"""Publication service for branch-stage lifecycle updates."""

from __future__ import annotations

from v3.contracts.branch import BranchSnapshot, BranchStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.ports.state_store import StateStorePort

_STAGE_ORDER = {stage_key: index for index, stage_key in enumerate(StageKey)}


class StageTransitionService:
    """Publishes later branch-stage updates through the V3 state store."""

    def __init__(self, state_store: StateStorePort) -> None:
        self._state_store = state_store

    def publish_stage_start(self, branch_id: str, stage_snapshot: StageSnapshot) -> BranchSnapshot:
        return self._publish_stage_snapshot(
            branch_id,
            stage_snapshot.model_copy(update={"status": StageStatus.IN_PROGRESS}),
        )

    def publish_stage_complete(self, branch_id: str, stage_snapshot: StageSnapshot) -> BranchSnapshot:
        branch = self._publish_stage_snapshot(
            branch_id,
            stage_snapshot.model_copy(update={"status": StageStatus.COMPLETED}),
        )
        if stage_snapshot.next_stage_key is None:
            return branch

        next_stage = StageSnapshot(
            stage_key=stage_snapshot.next_stage_key,
            stage_iteration=1,
            status=StageStatus.NOT_STARTED,
            summary="Prepared and requires preflight before execution.",
            artifact_ids=[],
            next_stage_key=self._next_stage_key_for(stage_snapshot.next_stage_key),
        )
        return self._publish_stage_snapshot(branch_id, next_stage)

    def publish_stage_block(self, branch_id: str, stage_snapshot: StageSnapshot) -> BranchSnapshot:
        return self._publish_stage_snapshot(
            branch_id,
            stage_snapshot.model_copy(update={"status": StageStatus.BLOCKED}),
        )

    def publish_stage_replay(self, branch_id: str, stage_snapshot: StageSnapshot) -> BranchSnapshot:
        return self._publish_stage_snapshot(
            branch_id,
            stage_snapshot.model_copy(update={"status": StageStatus.IN_PROGRESS}),
        )

    def publish_stage_transition(self, branch_id: str, stage_snapshot: StageSnapshot) -> BranchSnapshot:
        return self._publish_stage_snapshot(branch_id, stage_snapshot)

    def _publish_stage_snapshot(self, branch_id: str, stage_snapshot: StageSnapshot) -> BranchSnapshot:
        branch = self._state_store.load_branch_snapshot(branch_id)
        if branch is None:
            raise KeyError(f"branch not found: {branch_id}")

        stages = [
            stage
            for stage in branch.stages
            if not (
                stage.stage_key == stage_snapshot.stage_key and stage.stage_iteration == stage_snapshot.stage_iteration
            )
        ]
        stages.append(stage_snapshot)
        stages.sort(key=lambda stage: (_STAGE_ORDER[stage.stage_key], stage.stage_iteration))
        artifact_ids = list(dict.fromkeys([*branch.artifact_ids, *stage_snapshot.artifact_ids]))
        updated_branch = branch.model_copy(
            update={
                "current_stage_key": stage_snapshot.stage_key,
                "stages": stages,
                "status": self._branch_status_for_stage(stage_snapshot),
                "artifact_ids": artifact_ids,
            }
        )
        self._state_store.write_stage_snapshot(branch_id, stage_snapshot)
        self._state_store.write_branch_snapshot(updated_branch)
        return updated_branch

    def _branch_status_for_stage(self, stage_snapshot: StageSnapshot) -> BranchStatus:
        if stage_snapshot.status is StageStatus.BLOCKED:
            return BranchStatus.BLOCKED
        if stage_snapshot.status is StageStatus.COMPLETED and stage_snapshot.next_stage_key is None:
            return BranchStatus.COMPLETED
        return BranchStatus.ACTIVE

    def _next_stage_key_for(self, stage_key: StageKey) -> StageKey | None:
        next_index = _STAGE_ORDER[stage_key] + 1
        if next_index >= len(StageKey):
            return None
        return tuple(StageKey)[next_index]


__all__ = ["StageTransitionService"]
