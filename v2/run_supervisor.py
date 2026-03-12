from __future__ import annotations

import threading
from typing import Any

from v2.models import RunStatus
from v2.run_service import V2RunService


class V2RunSupervisor:
    def __init__(self, run_service: V2RunService | None = None) -> None:
        self._run_service = run_service or V2RunService()
        self._lock = threading.Lock()
        self._workers: dict[str, threading.Thread] = {}
        self._controls: dict[str, str] = {}
        self._recover_inflight_runs()

    def create_run(self, config: dict[str, Any]) -> str:
        run_id = self._run_service.create_run(config)
        self._start_worker(run_id, config)
        return run_id

    def pause_run(self, run_id: str) -> None:
        with self._lock:
            if run_id not in self._controls:
                raise KeyError(f"run not found: {run_id}")
            self._controls[run_id] = "pause"

    def resume_run(self, run_id: str) -> None:
        with self._lock:
            self._controls[run_id] = "run"
            worker = self._workers.get(run_id)

        if worker is None or not worker.is_alive():
            run = self._run_service._runs.get(run_id, {})
            config = run.get("config", {})
            self._start_worker(run_id, config)

    def stop_run(self, run_id: str) -> None:
        with self._lock:
            self._controls[run_id] = "stop"

    def get_status(self, run_id: str) -> str:
        return self._run_service.get_status(run_id)

    def _start_worker(self, run_id: str, config: dict[str, Any]) -> None:
        with self._lock:
            self._controls[run_id] = "run"
            worker = threading.Thread(
                target=self._worker_loop,
                args=(run_id, config),
                daemon=True,
                name=f"v2-supervisor-{run_id}",
            )
            self._workers[run_id] = worker
        worker.start()

    def _worker_loop(self, run_id: str, config: dict[str, Any]) -> None:
        try:
            if config.get("_force_worker_error"):
                raise RuntimeError("forced worker error")

            control = self._controls.get(run_id, "run")
            if control == "stop":
                return

            self._run_service.start_run(run_id)
        except Exception:
            try:
                run = self._run_service._runs.get(run_id)
                if run:
                    run["status"] = RunStatus.FAILED.value
            except Exception:
                pass
        finally:
            with self._lock:
                self._workers.pop(run_id, None)

    def _recover_inflight_runs(self) -> list[str]:
        recovered: list[str] = []
        for run_id, run_data in list(self._run_service._runs.items()):
            if run_data.get("status") == RunStatus.RUNNING.value:
                run_data["status"] = RunStatus.PAUSED.value
                config = run_data.setdefault("config", {})
                if isinstance(config, dict):
                    config["recovery_required"] = True
                recovered.append(run_id)
        return recovered

    def _inject_test_run(self, run_id: str, status: str) -> None:
        self._run_service._runs[run_id] = {
            "config": {},
            "status": status,
        }


__all__ = ["V2RunSupervisor"]
