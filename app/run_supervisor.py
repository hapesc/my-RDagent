"""Background run supervision for the Task-21 control plane."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from app.runtime import build_run_service, build_runtime
from data_models import RunSession, RunStatus
from service_contracts import ErrorCode, RunCreateRequest, ServiceContractError


@dataclass
class RunSupervisorConfig:
    """Supervisor execution cadence and restart policy."""

    loop_poll_interval_sec: float = 0.01
    default_loops_per_call: int = 1


class RunSupervisor:
    """Runs loop iterations in the background and exposes lifecycle controls."""

    _VALID_TRANSITIONS = {
        "pause": {RunStatus.CREATED, RunStatus.RUNNING},
        "resume": {RunStatus.PAUSED, RunStatus.FAILED},
        "stop": {RunStatus.CREATED, RunStatus.RUNNING, RunStatus.PAUSED, RunStatus.FAILED},
    }
    _ACTION_LABELS = {
        "pause": "paused",
        "resume": "resumed",
        "stop": "stopped",
    }

    def __init__(self, config: RunSupervisorConfig | None = None) -> None:
        self._config = config or RunSupervisorConfig()
        self._lock = threading.Lock()
        self._workers: dict[str, threading.Thread] = {}
        self._controls: dict[str, str] = {}
        self._recover_inflight_runs()

    def create_run(self, request: RunCreateRequest, config_snapshot: dict[str, Any]) -> RunSession:
        runtime = build_runtime()
        run_service = build_run_service(runtime, request.scenario)
        run_session = run_service.create_run(
            task_summary=request.task_summary,
            scenario=request.scenario,
            stop_conditions=request.stop_conditions,
            run_id=request.run_id,
            entry_input={**request.entry_input, "task_summary": request.task_summary},
            config_snapshot=config_snapshot,
        )
        self.start_background(run_session.run_id, request.task_summary, request.scenario)
        return run_session

    def start_background(
        self,
        run_id: str,
        task_summary: str,
        scenario: str,
        *,
        resume: bool = False,
    ) -> None:
        with self._lock:
            worker = self._workers.get(run_id)
            if worker is not None and worker.is_alive():
                return
            self._controls[run_id] = "run"
            worker = threading.Thread(
                target=self._worker_loop,
                args=(run_id, task_summary, scenario, resume),
                daemon=True,
                name=f"run-supervisor-{run_id}",
            )
            self._workers[run_id] = worker
            worker.start()

    def pause_run(self, run_id: str) -> RunSession:
        run_session = self._require_actionable_run(run_id, action="pause")
        with self._lock:
            self._controls[run_id] = "pause"
        return run_session

    def resume_run(self, run_id: str) -> RunSession:
        run_session = self._require_actionable_run(run_id, action="resume")
        task_summary = str(run_session.entry_input.get("task_summary", "resume"))
        self.start_background(run_id, task_summary, run_session.scenario, resume=True)
        return run_session

    def stop_run(self, run_id: str) -> RunSession:
        run_session = self._require_actionable_run(run_id, action="stop")
        if run_session.status in {RunStatus.PAUSED, RunStatus.FAILED}:
            run_session.update_status(RunStatus.STOPPED)
            runtime = build_runtime()
            runtime.sqlite_store.create_run(run_session)
            return run_session
        with self._lock:
            self._controls[run_id] = "stop"
        return run_session

    def wait_for_idle(self, run_id: str, timeout_sec: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            with self._lock:
                worker = self._workers.get(run_id)
            if worker is None or not worker.is_alive():
                return True
            time.sleep(self._config.loop_poll_interval_sec)
        return False

    def _worker_loop(self, run_id: str, task_summary: str, scenario: str, resume: bool) -> None:
        runtime = build_runtime()
        run_service = build_run_service(runtime, scenario)
        first_call = True
        try:
            while True:
                control = self._controls.get(run_id, "run")
                if control == "stop":
                    run_service.stop_run(run_id)
                    break
                if control == "pause" and not first_call:
                    self._mark_paused(run_id)
                    break

                if resume or not first_call:
                    context = run_service.resume_run(
                        run_id=run_id,
                        task_summary=task_summary,
                        loops_per_call=self._config.default_loops_per_call,
                    )
                else:
                    context = run_service.start_run(
                        run_id=run_id,
                        task_summary=task_summary,
                        loops_per_call=self._config.default_loops_per_call,
                    )

                first_call = False
                resume = True
                if context.run_session.status in {RunStatus.COMPLETED, RunStatus.STOPPED, RunStatus.FAILED}:
                    break
                if self._controls.get(run_id) == "pause":
                    self._mark_paused(run_id)
                    break
                time.sleep(self._config.loop_poll_interval_sec)
        finally:
            with self._lock:
                self._workers.pop(run_id, None)
                self._controls.pop(run_id, None)

    def _mark_paused(self, run_id: str) -> None:
        runtime = build_runtime()
        run_session = runtime.sqlite_store.get_run(run_id)
        if run_session is None:
            return
        if run_session.status != RunStatus.PAUSED:
            run_session.update_status(RunStatus.PAUSED)
            runtime.sqlite_store.create_run(run_session)

    def _recover_inflight_runs(self) -> None:
        runtime = build_runtime()
        for run_session in runtime.sqlite_store.list_runs():
            if run_session.status != RunStatus.RUNNING:
                continue
            run_session.update_status(RunStatus.PAUSED)
            run_session.entry_input["recovery_required"] = True
            runtime.sqlite_store.create_run(run_session)

    def _require_actionable_run(self, run_id: str, *, action: str) -> RunSession:
        runtime = build_runtime()
        run_session = runtime.sqlite_store.get_run(run_id)
        if run_session is None:
            raise KeyError(f"run not found: {run_id}")
        allowed_statuses = self._VALID_TRANSITIONS[action]
        if run_session.status not in allowed_statuses:
            raise ServiceContractError(
                code=ErrorCode.INVALID_STATE,
                message=f"run {run_id} cannot be {self._ACTION_LABELS[action]} from status {run_session.status}",
            )
        return run_session
