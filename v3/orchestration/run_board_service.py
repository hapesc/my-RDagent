"""Publication service for V3 run-board and branch snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from v3.contracts.artifact import ArtifactSnapshot
from v3.contracts.branch import BranchSnapshot
from v3.contracts.run import RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageSnapshot
from v3.contracts.tool_io import RunStartRequest
from v3.ports.execution import ExecutionPort
from v3.ports.state_store import StateStorePort


@dataclass(frozen=True)
class RunBoardPublication:
    run: RunBoardSnapshot
    branch: BranchSnapshot


@dataclass(frozen=True)
class RunStartPublication:
    run: RunBoardSnapshot
    branch: BranchSnapshot
    stage: StageSnapshot
    artifacts: list[ArtifactSnapshot]


class RunBoardService:
    """Publishes canonical run-board and branch truth."""

    def __init__(
        self,
        state_store: StateStorePort,
        execution_port: ExecutionPort | None = None,
    ) -> None:
        self._state_store = state_store
        self._execution_port = execution_port

    def publish(self, run: RunBoardSnapshot, branch: BranchSnapshot) -> RunBoardPublication:
        self._state_store.write_run_snapshot(run)
        self._state_store.write_branch_snapshot(branch)
        return RunBoardPublication(run=run, branch=branch)

    def get_run(self, run_id: str) -> RunBoardSnapshot | None:
        return self._state_store.load_run_snapshot(run_id)

    def append_branch(
        self,
        *,
        run_id: str,
        branch: BranchSnapshot,
        latest_branch_decision_id: str | None = None,
        latest_branch_board_id: str | None = None,
        exploration_mode=None,
    ) -> RunBoardPublication:
        run = self._state_store.load_run_snapshot(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")

        branch_ids = list(run.branch_ids)
        if branch.branch_id not in branch_ids:
            branch_ids.append(branch.branch_id)

        updated_run = run.model_copy(
            update={
                "branch_ids": branch_ids,
                "latest_branch_decision_id": latest_branch_decision_id or run.latest_branch_decision_id,
                "latest_branch_board_id": latest_branch_board_id or run.latest_branch_board_id,
                "exploration_mode": exploration_mode or run.exploration_mode,
            }
        )
        return self.publish(updated_run, branch)

    def start_run(self, request: RunStartRequest) -> RunStartPublication:
        if self._execution_port is None:
            raise RuntimeError("execution port is required to start a run")

        execution_result = self._execution_port.start_run(request)
        branch = execution_result.branch
        stage = execution_result.stage
        artifacts = list(execution_result.artifacts)

        self._state_store.write_branch_snapshot(branch)
        self._state_store.write_stage_snapshot(branch.branch_id, stage)
        for artifact in artifacts:
            self._state_store.write_artifact_snapshot(artifact)

        run = RunBoardSnapshot(
            run_id=branch.run_id,
            title=request.title,
            scenario_label=request.scenario_label,
            status=RunStatus.ACTIVE,
            exploration_mode=request.exploration_mode,
            primary_branch_id=branch.branch_id,
            branch_ids=[branch.branch_id],
            highlighted_artifact_ids=[artifact.artifact_id for artifact in artifacts],
            summary=request.task_summary,
        )
        self._state_store.write_run_snapshot(run)
        return RunStartPublication(run=run, branch=branch, stage=stage, artifacts=artifacts)


__all__ = ["RunBoardPublication", "RunBoardService", "RunStartPublication"]
