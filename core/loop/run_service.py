"""Run service and resume manager for loop lifecycle control."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from core.execution import WorkspaceManager
from core.storage import BranchTraceStore
from core.storage.interfaces import CheckpointStore, RunMetadataStore
from data_models import LoopContext, RunSession, RunStatus, StopConditions


@dataclass
class RunServiceConfig:
    """Run service defaults."""

    default_scenario: str = "data_science"


class ResumeManager:
    """Resolves resume point from persisted checkpoints."""

    _CHECKPOINT_PATTERN = re.compile(r"^loop-(\d+)-([a-z_]+)$")
    _STEP_ORDER = {
        "propose": 0,
        "experiment": 1,
        "coding": 2,
        "running": 3,
        "feedback": 4,
        "record": 5,
    }

    def __init__(self, checkpoint_store: CheckpointStore, workspace_manager: WorkspaceManager) -> None:
        self._checkpoint_store = checkpoint_store
        self._workspace_manager = workspace_manager

    def latest_checkpoint(self, run_id: str) -> str | None:
        checkpoints = self._checkpoint_store.list_checkpoints(run_id)
        if not checkpoints:
            return None
        return max(checkpoints, key=self._checkpoint_sort_key)

    def next_iteration(self, run_id: str) -> int:
        checkpoint_id = self.latest_checkpoint(run_id)
        if checkpoint_id is None:
            return 0
        parsed = self._parse_checkpoint_id(checkpoint_id)
        if parsed is None:
            return 0
        loop_index, step_name = parsed
        if step_name == "record":
            return loop_index + 1
        return loop_index

    def restore_latest(self, run_id: str) -> str | None:
        checkpoint_id = self.latest_checkpoint(run_id)
        if checkpoint_id is None:
            return None
        return self.restore_checkpoint(run_id, checkpoint_id)

    def restore_checkpoint(self, run_id: str, checkpoint_id: str) -> str | None:
        parsed = self._parse_checkpoint_id(checkpoint_id)
        workspace_id = "resume-latest" if parsed is None else f"resume-{parsed[0]:04d}"
        workspace_path = self._workspace_manager.workspace_path(run_id, workspace_id)
        self._workspace_manager.restore_checkpoint(run_id, checkpoint_id, workspace_path)
        return workspace_path

    def _parse_checkpoint_id(self, checkpoint_id: str) -> tuple[int, str] | None:
        match = self._CHECKPOINT_PATTERN.match(checkpoint_id)
        if match is None:
            return None
        return int(match.group(1)), match.group(2)

    def _checkpoint_sort_key(self, checkpoint_id: str) -> tuple[int, int]:
        parsed = self._parse_checkpoint_id(checkpoint_id)
        if parsed is None:
            return (-1, -1)
        loop_index, step_name = parsed
        return (loop_index, self._STEP_ORDER.get(step_name, -1))


class RunService:
    """Controls run lifecycle and resume semantics."""

    def __init__(
        self,
        config: RunServiceConfig,
        loop_engine,
        run_store: RunMetadataStore,
        resume_manager: ResumeManager,
        branch_store: BranchTraceStore | None = None,
    ) -> None:
        self._config = config
        self._loop_engine = loop_engine
        self._run_store = run_store
        self._resume_manager = resume_manager
        self._branch_store = branch_store

    def create_run(
        self,
        task_summary: str,
        scenario: str | None = None,
        stop_conditions: StopConditions | None = None,
        run_id: str | None = None,
        entry_input: dict[str, Any] | None = None,
        config_snapshot: dict[str, Any] | None = None,
    ) -> RunSession:
        session_entry_input = dict(entry_input or {})
        session_entry_input["task_summary"] = task_summary
        session = RunSession(
            run_id=run_id or f"run-{uuid.uuid4().hex[:12]}",
            scenario=scenario or self._config.default_scenario,
            status=RunStatus.CREATED,
            stop_conditions=stop_conditions or StopConditions(),
            entry_input=session_entry_input,
            config_snapshot=dict(config_snapshot or {}),
        )
        self._run_store.create_run(session)
        return session

    def get_run(self, run_id: str) -> RunSession | None:
        return self._run_store.get_run(run_id)

    def start_run(self, run_id: str, task_summary: str, loops_per_call: int | None = None) -> LoopContext:
        run_session = self._require_run(run_id)
        if run_session.status in {RunStatus.COMPLETED, RunStatus.STOPPED}:
            raise RuntimeError(f"run {run_id} cannot be started from status {run_session.status}")

        start_iteration = self._resume_manager.next_iteration(run_id)
        restored_workspace: str | None = None
        restore_checkpoint_id = run_session.entry_input.pop("fork_checkpoint_id", None)
        fork_start_iteration = run_session.entry_input.pop("fork_start_iteration", None)
        try:
            if restore_checkpoint_id is not None:
                start_iteration = int(fork_start_iteration or 0)
                restored_workspace = self._resume_manager.restore_checkpoint(run_id, str(restore_checkpoint_id))
            elif start_iteration > 0:
                restored_workspace = self._resume_manager.restore_latest(run_id)
        except Exception as exc:
            message = f"checkpoint restore failed for run {run_id}: {exc}"
            run_session.entry_input["last_error"] = message
            run_session.update_status(RunStatus.FAILED)
            self._run_store.create_run(run_session)
            raise RuntimeError(message) from exc

        context = self._loop_engine.run(
            run_session=run_session,
            task_summary=task_summary,
            max_loops=loops_per_call,
            start_iteration=start_iteration,
            restored_workspace=restored_workspace,
        )
        self._run_store.create_run(context.run_session)
        if context.run_session.status == RunStatus.FAILED:
            message = str(context.run_session.entry_input.get("last_error", "run failed"))
            raise RuntimeError(message)
        return context

    def fork_branch(self, run_id: str, parent_node_id: str | None = None) -> RunSession:
        if self._branch_store is None:
            raise RuntimeError("branch store is not configured")

        run_session = self._require_run(run_id)
        current_branch = run_session.active_branch_ids[0] if run_session.active_branch_ids else "main"
        branch_heads = self._branch_store.get_branch_heads(run_id)
        resolved_parent_node_id = parent_node_id or branch_heads.get(current_branch)
        if resolved_parent_node_id is None:
            raise RuntimeError(f"branch head not found for run {run_id} branch {current_branch}")

        parent_node = self._branch_store.get_node(run_id, resolved_parent_node_id)
        if parent_node is None:
            raise KeyError(f"parent node not found: {run_id}/{resolved_parent_node_id}")

        new_branch_id = f"{parent_node.branch_id}-fork-{uuid.uuid4().hex[:6]}"
        run_session.active_branch_ids = [new_branch_id]
        run_session.stop_conditions.max_loops = max(
            run_session.stop_conditions.max_loops,
            parent_node.loop_index + 2,
        )
        run_session.entry_input["fork_parent_node_id"] = parent_node.node_id
        run_session.entry_input["fork_checkpoint_id"] = f"loop-{parent_node.loop_index:04d}-record"
        run_session.entry_input["fork_start_iteration"] = parent_node.loop_index + 1
        run_session.update_status(RunStatus.PAUSED)
        self._run_store.create_run(run_session)
        return run_session

    def pause_run(self, run_id: str) -> RunSession:
        run_session = self._require_run(run_id)
        if run_session.status != RunStatus.RUNNING:
            raise RuntimeError(f"run {run_id} cannot be paused from status {run_session.status}")
        run_session.update_status(RunStatus.PAUSED)
        self._run_store.create_run(run_session)
        return run_session

    def resume_run(self, run_id: str, task_summary: str, loops_per_call: int | None = None) -> LoopContext:
        run_session = self._require_run(run_id)
        if run_session.status not in {RunStatus.PAUSED, RunStatus.RUNNING, RunStatus.FAILED}:
            raise RuntimeError(f"run {run_id} cannot be resumed from status {run_session.status}")
        run_session.update_status(RunStatus.RUNNING)
        self._run_store.create_run(run_session)
        return self.start_run(run_id=run_id, task_summary=task_summary, loops_per_call=loops_per_call)

    def stop_run(self, run_id: str) -> RunSession:
        run_session = self._require_run(run_id)
        run_session.update_status(RunStatus.STOPPED)
        self._run_store.create_run(run_session)
        return run_session

    def _require_run(self, run_id: str) -> RunSession:
        run_session = self._run_store.get_run(run_id)
        if run_session is None:
            raise KeyError(f"run not found: {run_id}")
        return run_session
