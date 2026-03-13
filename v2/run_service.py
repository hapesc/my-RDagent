from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from v2.graph.main_loop import build_main_graph
from v2.models import RunStatus

try:
    from langgraph.checkpoint.sqlite import SqliteSaver

    _HAS_SQLITE_SAVER = True
except ImportError:
    _HAS_SQLITE_SAVER = False


class _CooperativePauseRequested(Exception):
    pass


class V2RunService:
    def __init__(
        self,
        plugin_registry: Any = None,
        checkpoint_coordinator: Any = None,
        sqlite_path: str | None = None,
    ) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._plugin_registry = plugin_registry
        self.checkpoint_coordinator = checkpoint_coordinator
        self._pause_probe: Callable[[str], bool] | None = None
        self._sqlite_path = sqlite_path or ":memory:"

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

            last_completed_node = recovered_payload.get("last_completed_node")
            next_node = recovered_payload.get("next_node")
            if next_node is None:
                raise ValueError("Invalid recovery payload: next_node is None")

            self._execute(
                run_id,
                run,
                initial_state=restored_state,
                resume_as_node=str(last_completed_node),
                expected_next_node=str(next_node),
            )
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

    def _resolve_plugins(self, run: dict[str, Any]) -> dict[str, Any]:
        config = run["config"]
        scenario = config.get("scenario")
        plugins: dict[str, Any] = {}
        if scenario and self._plugin_registry is not None:
            try:
                bundle = self._plugin_registry.get(scenario)
                plugins["proposer_plugin"] = bundle.proposer
                plugins["coder_plugin"] = bundle.coder
                plugins["runner_plugin"] = bundle.runner
                plugins["evaluator_plugin"] = bundle.evaluator
            except KeyError:
                pass
        return plugins

    def _execute(
        self,
        run_id: str,
        run: dict[str, Any],
        *,
        initial_state: dict[str, Any] | None = None,
        resume_as_node: str | None = None,
        expected_next_node: str | None = None,
    ) -> None:
        use_sqlite = (
            _HAS_SQLITE_SAVER
            and self._sqlite_path != ":memory:"
        )
        if use_sqlite:
            conn = sqlite3.connect(self._sqlite_path, check_same_thread=False)
            checkpointer = SqliteSaver(conn)
            try:
                self._run_graph(
                    run_id, run, checkpointer,
                    initial_state=initial_state,
                    resume_as_node=resume_as_node,
                    expected_next_node=expected_next_node,
                )
            finally:
                conn.close()
        else:
            checkpointer = MemorySaver()
            self._run_graph(
                run_id, run, checkpointer,
                initial_state=initial_state,
                resume_as_node=resume_as_node,
                expected_next_node=expected_next_node,
            )

    def _run_graph(
        self,
        run_id: str,
        run: dict[str, Any],
        checkpointer: Any,
        *,
        initial_state: dict[str, Any] | None = None,
        resume_as_node: str | None = None,
        expected_next_node: str | None = None,
    ) -> None:
        plugins = self._resolve_plugins(run)
        graph = build_main_graph(checkpointer=checkpointer, **plugins)
        config: dict[str, Any] = {"configurable": {"thread_id": run_id}}

        if resume_as_node is not None:
            graph.update_state(config, initial_state, as_node=resume_as_node)
            input_state = None
            accumulated_state = dict(initial_state) if initial_state else {}
        else:
            expected_next_node = None  # only meaningful for resume path
            if initial_state is None:
                run_config = run["config"]
                input_state: dict[str, Any] = {
                    "run_id": run_id,
                    "loop_iteration": 0,
                    "max_loops": int(run_config.get("max_loops", 1)),
                    "tokens_used": 0,
                    "token_budget": int(run_config.get("token_budget", 0)),
                    "costeer_max_rounds": int(run_config.get("costeer_max_rounds", 3)),
                }
                if run_config.get("task_summary"):
                    input_state["task_summary"] = run_config["task_summary"]
            else:
                input_state = dict(initial_state)
            accumulated_state = dict(input_state)

        # Deferred checkpoint approach: save node N's checkpoint when node N+1 starts.
        # This lets us set next_node accurately.
        pending: dict[str, Any] | None = None
        paused = False

        for event in graph.stream(input_state, config, stream_mode="updates", durability="async"):
            node_name = list(event.keys())[0]
            if node_name.startswith("__"):
                continue

            # On resume, verify the first executed node matches the checkpoint's next_node.
            if expected_next_node is not None:
                if node_name != expected_next_node:
                    raise ValueError(
                        f"Resume integrity check failed: checkpoint says next_node={expected_next_node!r}, "
                        f"but graph executed {node_name!r}"
                    )
                expected_next_node = None  # check only once

            # Save checkpoint for the PREVIOUS node (we now know its next_node).
            if pending is not None and self.checkpoint_coordinator is not None:
                pending["next_node"] = node_name
                ckpt_id = self.checkpoint_coordinator.save(
                    name=f"run-{run_id}-node-{pending['last_completed_node']}",
                    workspace_data=b"",
                    state=pending,
                )
                run["latest_checkpoint_id"] = ckpt_id

            # Apply updates to our accumulated state.
            node_updates = event[node_name]
            if node_updates:
                accumulated_state = {**accumulated_state, **node_updates}

            pending = {
                "run_id": run_id,
                "loop_iteration": int(accumulated_state.get("loop_iteration", 0)),
                "last_completed_node": node_name,
                "state": dict(accumulated_state),
            }

            # Cooperative pause check.
            if self._pause_probe is not None and self._pause_probe(run_id):
                paused = True
                break

        if paused:
            # After breaking the stream, get_state() returns correct next info.
            snapshot = graph.get_state(config)
            next_nodes = snapshot.next
            if pending is not None and self.checkpoint_coordinator is not None:
                pending["next_node"] = next_nodes[0] if next_nodes else None
                ckpt_id = self.checkpoint_coordinator.save(
                    name=f"run-{run_id}-node-{pending['last_completed_node']}-pause",
                    workspace_data=b"",
                    state=pending,
                )
                run["latest_checkpoint_id"] = ckpt_id
            run["status"] = RunStatus.PAUSED.value
            raise _CooperativePauseRequested()

        # Save final checkpoint (next_node=None means graph is done).
        if pending is not None and self.checkpoint_coordinator is not None:
            pending["next_node"] = None
            ckpt_id = self.checkpoint_coordinator.save(
                name=f"run-{run_id}-node-{pending['last_completed_node']}",
                workspace_data=b"",
                state=pending,
            )
            run["latest_checkpoint_id"] = ckpt_id

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
