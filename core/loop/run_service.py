"""Run service and resume manager for loop lifecycle control."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Optional

from core.execution import WorkspaceManager
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

    def latest_checkpoint(self, run_id: str) -> Optional[str]:
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

    def restore_latest(self, run_id: str) -> Optional[str]:
        checkpoint_id = self.latest_checkpoint(run_id)
        if checkpoint_id is None:
            return None
        parsed = self._parse_checkpoint_id(checkpoint_id)
        workspace_id = "resume-latest" if parsed is None else f"resume-{parsed[0]:04d}"
        workspace_path = self._workspace_manager.create_workspace(run_id, workspace_id)
        self._workspace_manager.restore_checkpoint(run_id, checkpoint_id, workspace_path)
        return workspace_path

    def _parse_checkpoint_id(self, checkpoint_id: str) -> Optional[tuple[int, str]]:
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
    ) -> None:
        self._config = config
        self._loop_engine = loop_engine
        self._run_store = run_store
        self._resume_manager = resume_manager

    def create_run(
        self,
        task_summary: str,
        scenario: Optional[str] = None,
        stop_conditions: Optional[StopConditions] = None,
        run_id: Optional[str] = None,
    ) -> RunSession:
        session = RunSession(
            run_id=run_id or f"run-{uuid.uuid4().hex[:12]}",
            scenario=scenario or self._config.default_scenario,
            status=RunStatus.CREATED,
            stop_conditions=stop_conditions or StopConditions(),
            entry_input={"task_summary": task_summary},
        )
        self._run_store.create_run(session)
        return session

    def get_run(self, run_id: str) -> Optional[RunSession]:
        return self._run_store.get_run(run_id)

    def start_run(self, run_id: str, task_summary: str, loops_per_call: Optional[int] = None) -> LoopContext:
        run_session = self._require_run(run_id)
        if run_session.status in {RunStatus.COMPLETED, RunStatus.STOPPED}:
            raise RuntimeError(f"run {run_id} cannot be started from status {run_session.status}")

        start_iteration = self._resume_manager.next_iteration(run_id)
        if start_iteration > 0:
            self._resume_manager.restore_latest(run_id)

        context = self._loop_engine.run(
            run_session=run_session,
            task_summary=task_summary,
            max_loops=loops_per_call,
            start_iteration=start_iteration,
        )
        self._run_store.create_run(context.run_session)
        return context

    def pause_run(self, run_id: str) -> RunSession:
        run_session = self._require_run(run_id)
        if run_session.status != RunStatus.RUNNING:
            raise RuntimeError(f"run {run_id} cannot be paused from status {run_session.status}")
        run_session.update_status(RunStatus.PAUSED)
        self._run_store.create_run(run_session)
        return run_session

    def resume_run(self, run_id: str, task_summary: str, loops_per_call: Optional[int] = None) -> LoopContext:
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
