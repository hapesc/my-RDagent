from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, cast

from v2.graph.main_loop import build_main_graph
from v2.models import RunStatus


class V2RunService:
    def __init__(self, plugin_registry: Any = None) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._plugin_registry = plugin_registry

    def create_run(self, config: dict[str, Any]) -> str:
        run_id = str(uuid.uuid4())
        self._runs[run_id] = {
            "config": dict(config),
            "status": RunStatus.CREATED.value,
        }
        return run_id

    def start_run(self, run_id: str) -> None:
        run = self._require_run(run_id)
        self._transition(run_id, expected=RunStatus.CREATED.value, target=RunStatus.RUNNING.value, action="start")

        try:
            self._execute(run_id, run)
            if run["status"] == RunStatus.RUNNING.value:
                run["status"] = RunStatus.COMPLETED.value
        except Exception:
            run["status"] = RunStatus.FAILED.value
            raise

    def pause_run(self, run_id: str) -> None:
        self._transition(run_id, expected=RunStatus.RUNNING.value, target=RunStatus.PAUSED.value, action="pause")

    def resume_run(self, run_id: str) -> None:
        run = self._require_run(run_id)
        self._transition(run_id, expected=RunStatus.PAUSED.value, target=RunStatus.RUNNING.value, action="resume")
        try:
            self._execute(run_id, run)
            if run["status"] == RunStatus.RUNNING.value:
                run["status"] = RunStatus.COMPLETED.value
        except Exception:
            run["status"] = RunStatus.FAILED.value
            raise

    def stop_run(self, run_id: str) -> None:
        run = self._require_run(run_id)
        if run["status"] not in {RunStatus.RUNNING.value, RunStatus.PAUSED.value}:
            raise ValueError(f"Cannot stop run in status {run['status']}")
        run["status"] = RunStatus.STOPPED.value

    def fork_run(self, run_id: str) -> str:
        source_run = self._require_run(run_id)
        fork_id = str(uuid.uuid4())
        self._runs[fork_id] = {
            "config": dict(source_run["config"]),
            "status": RunStatus.CREATED.value,
            "forked_from": run_id,
        }
        return fork_id

    def get_status(self, run_id: str) -> str:
        run = self._require_run(run_id)
        return str(run["status"])

    def _execute(self, run_id: str, run: dict[str, Any]) -> None:
        graph = build_main_graph()
        config = run["config"]
        initial_state: dict[str, Any] = {
            "run_id": run_id,
            "loop_iteration": 0,
            "max_loops": int(config.get("max_loops", 1)),
        }
        if config.get("task_summary"):
            initial_state["task_summary"] = config["task_summary"]

        scenario = config.get("scenario")
        if scenario and self._plugin_registry is not None:
            try:
                bundle = self._plugin_registry.get(scenario)
                initial_state["_proposer_plugin"] = bundle.proposer
                initial_state["_coder_plugin"] = bundle.coder
                initial_state["_runner_plugin"] = bundle.runner
                initial_state["_evaluator_plugin"] = bundle.evaluator
            except KeyError:
                pass

        invoke_fn = self._as_invoke(graph)
        invoke_fn(initial_state)

    def _as_invoke(self, graph: Any) -> Callable[[dict[str, Any]], dict[str, Any]]:
        invoke = getattr(graph, "invoke", None)
        if not callable(invoke):
            raise TypeError("Compiled graph does not provide callable invoke")
        return cast(Callable[[dict[str, Any]], dict[str, Any]], invoke)

    def _transition(self, run_id: str, expected: str, target: str, action: str) -> None:
        run = self._require_run(run_id)
        if run["status"] != expected:
            raise ValueError(f"Cannot {action} run in status {run['status']}")
        run["status"] = target

    def _require_run(self, run_id: str) -> dict[str, Any]:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run


__all__ = ["V2RunService"]
