from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, cast

from v2.graph.main_loop import build_main_graph
from v2.models import RunStatus


class _CooperativePauseRequested(Exception):
    pass


class V2RunService:
    def __init__(self, plugin_registry: Any = None, checkpoint_coordinator: Any = None) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._plugin_registry = plugin_registry
        self.checkpoint_coordinator = checkpoint_coordinator
        self._pause_probe: Callable[[str], bool] | None = None

    def set_pause_probe(self, pause_probe: Callable[[str], bool] | None) -> None:
        self._pause_probe = pause_probe

    def create_run(self, config: dict[str, Any]) -> str:
        run_id = str(uuid.uuid4())
        self._runs[run_id] = {
            "config": dict(config),
            "status": RunStatus.CREATED.value,
            "latest_checkpoint_id": None,
        }
        return run_id

    def start_run(self, run_id: str) -> None:
        run = self._require_run(run_id)
        self._transition(run_id, expected=RunStatus.CREATED.value, target=RunStatus.RUNNING.value, action="start")

        try:
            self._execute(run_id, run)
            if run["status"] == RunStatus.RUNNING.value:
                run["status"] = RunStatus.COMPLETED.value
        except _CooperativePauseRequested:
            return
        except Exception:
            run["status"] = RunStatus.FAILED.value
            raise

    def pause_run(self, run_id: str) -> None:
        self._transition(run_id, expected=RunStatus.RUNNING.value, target=RunStatus.PAUSED.value, action="pause")

    def resume_run(self, run_id: str) -> None:
        run = self._require_run(run_id)
        self._transition(run_id, expected=RunStatus.PAUSED.value, target=RunStatus.RUNNING.value, action="resume")
        try:
            latest_checkpoint_id = run.get("latest_checkpoint_id")
            if not latest_checkpoint_id:
                raise ValueError("Cannot resume run without latest_checkpoint_id")
            if self.checkpoint_coordinator is None:
                raise ValueError("Cannot resume run without checkpoint coordinator")

            try:
                _workspace_data, recovered_payload = self.checkpoint_coordinator.restore(str(latest_checkpoint_id))
            except Exception as exc:
                raise ValueError("Failed to restore checkpoint") from exc

            if recovered_payload.get("run_id") != run_id:
                raise ValueError("Invalid recovery payload: run_id mismatch")

            restored_state = recovered_payload.get("state")
            if not isinstance(restored_state, dict):
                raise ValueError("Invalid recovery payload: missing state")

            next_node = recovered_payload.get("next_node")
            if next_node is None:
                raise ValueError("Invalid recovery payload: next_node is None")

            self._execute(run_id, run, initial_state=restored_state, start_node=str(next_node))
            if run["status"] == RunStatus.RUNNING.value:
                run["status"] = RunStatus.COMPLETED.value
        except _CooperativePauseRequested:
            return
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

    def _execute(
        self,
        run_id: str,
        run: dict[str, Any],
        *,
        initial_state: dict[str, Any] | None = None,
        start_node: str | None = None,
    ) -> None:
        graph = build_main_graph()
        config = run["config"]
        if initial_state is None:
            graph_state: dict[str, Any] = {
                "run_id": run_id,
                "loop_iteration": 0,
                "max_loops": int(config.get("max_loops", 1)),
            }
            if config.get("task_summary"):
                graph_state["task_summary"] = config["task_summary"]
        else:
            graph_state = dict(initial_state)

        scenario = config.get("scenario")
        if scenario and self._plugin_registry is not None:
            try:
                bundle = self._plugin_registry.get(scenario)
                graph_state["_proposer_plugin"] = bundle.proposer
                graph_state["_coder_plugin"] = bundle.coder
                graph_state["_runner_plugin"] = bundle.runner
                graph_state["_evaluator_plugin"] = bundle.evaluator
            except KeyError:
                pass

        def _checkpoint_hook(last_completed_node: str, next_node: str | None, state_snapshot: dict[str, Any]) -> None:
            if self.checkpoint_coordinator is not None:
                payload = {
                    "run_id": run_id,
                    "loop_iteration": int(state_snapshot.get("loop_iteration", 0)),
                    "last_completed_node": last_completed_node,
                    "next_node": next_node,
                    "state": dict(state_snapshot),
                }
                checkpoint_id = self.checkpoint_coordinator.save(
                    name=f"run-{run_id}-node-{last_completed_node}",
                    workspace_data=b"",
                    state=payload,
                )
                run["latest_checkpoint_id"] = checkpoint_id

            if self._pause_probe is not None and self._pause_probe(run_id):
                run["status"] = RunStatus.PAUSED.value
                raise _CooperativePauseRequested()

        invoke_fn = self._as_invoke(graph)
        if start_node is None:
            invoke_fn(graph_state, checkpoint_hook=_checkpoint_hook)
        else:
            invoke_fn(graph_state, start_node=start_node, checkpoint_hook=_checkpoint_hook)

    def _as_invoke(self, graph: Any) -> Callable[..., dict[str, Any]]:
        invoke = getattr(graph, "invoke", None)
        if not callable(invoke):
            raise TypeError("Compiled graph does not provide callable invoke")
        return cast(Callable[..., dict[str, Any]], invoke)

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
