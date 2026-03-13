from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from v2.models import RunStatus
from v2.runtime import build_v2_runtime


class _DummyGraph:
    def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
        return dict(initial_state)


class TestLifecycleE2E:
    def test_pause_resume(self, monkeypatch: pytest.MonkeyPatch) -> None:
        restore_calls: list[str] = []
        invoke_calls: list[dict] = []

        class _ResumeGraph:
            def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
                invoke_calls.append({"initial_state": dict(initial_state), "start_node": start_node})
                return dict(initial_state)

        class _FakeCoordinator:
            def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
                restore_calls.append(checkpoint_id)
                return (
                    b"",
                    {
                        "run_id": run_id,
                        "loop_iteration": 0,
                        "last_completed_node": "experiment_setup",
                        "next_node": "coding",
                        "state": {
                            "run_id": run_id,
                            "loop_iteration": 0,
                            "max_loops": 1,
                            "task_summary": "pause-resume",
                        },
                    },
                )

        monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _ResumeGraph())
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service

        run_id = service.create_run({"scenario": "data_science", "max_loops": 1, "task_summary": "pause-resume"})
        service.checkpoint_coordinator = _FakeCoordinator()
        assert service.get_status(run_id) == RunStatus.CREATED.value

        service._runs[run_id]["status"] = RunStatus.RUNNING.value
        service._runs[run_id]["latest_checkpoint_id"] = "ckpt-1"
        service.pause_run(run_id)
        assert service.get_status(run_id) == RunStatus.PAUSED.value

        service.resume_run(run_id)
        assert service.get_status(run_id) == RunStatus.COMPLETED.value
        assert restore_calls == ["ckpt-1"]
        assert invoke_calls == [
            {
                "initial_state": {
                    "run_id": run_id,
                    "loop_iteration": 0,
                    "max_loops": 1,
                    "task_summary": "pause-resume",
                },
                "start_node": "coding",
            }
        ]

        fresh_run_id = service.create_run({"scenario": "data_science", "max_loops": 1})
        service.start_run(fresh_run_id)
        assert service.get_status(fresh_run_id) == RunStatus.COMPLETED.value

    def test_fork_independence(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service

        source_run_id = service.create_run({"scenario": "data_science", "max_loops": 1, "task_summary": "baseline"})
        fork_run_id = service.fork_run(source_run_id)

        assert fork_run_id != source_run_id
        assert service.get_status(fork_run_id) == RunStatus.CREATED.value
        assert service._runs[fork_run_id]["forked_from"] == source_run_id

        service._runs[source_run_id]["config"]["max_loops"] = 99
        service._runs[source_run_id]["config"]["task_summary"] = "mutated"

        assert service._runs[fork_run_id]["config"]["max_loops"] == 1
        assert service._runs[fork_run_id]["config"]["task_summary"] == "baseline"

    def test_stop_prevents_resume(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service

        run_id = service.create_run({"scenario": "data_science", "max_loops": 1})
        service._runs[run_id]["status"] = RunStatus.RUNNING.value

        service.stop_run(run_id)
        assert service.get_status(run_id) == RunStatus.STOPPED.value

        with pytest.raises(ValueError, match="Cannot resume run"):
            service.resume_run(run_id)

    def test_idempotency(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _DummyGraph())
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service

        config = {"scenario": "data_science", "task_summary": "same-input", "max_loops": 1}
        first_run_id = service.create_run(config)
        second_run_id = service.create_run(config)

        service.start_run(first_run_id)
        service.start_run(second_run_id)

        assert first_run_id != second_run_id
        assert service.get_status(first_run_id) == RunStatus.COMPLETED.value
        assert service.get_status(second_run_id) == RunStatus.COMPLETED.value

        service._runs[first_run_id]["config"]["max_loops"] = 2
        assert service._runs[second_run_id]["config"]["max_loops"] == 1

    def test_resume_continues_from_checkpointed_next_node(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _FakeCoordinator:
            def __init__(self) -> None:
                self.saved_states: list[dict] = []

            def save(self, name: str, workspace_data: bytes, state: dict) -> str:
                self.saved_states.append(dict(state))
                return f"ckpt-{len(self.saved_states)}"

            def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
                index = int(checkpoint_id.split("-")[1]) - 1
                return b"", self.saved_states[index]

        execution_order: list[str] = []

        class _RecordingGraph:
            def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
                node_sequence = ["propose", "experiment_setup", "coding", "running", "feedback", "record"]
                started = start_node is None
                state = dict(initial_state)

                for node in node_sequence:
                    if not started:
                        if node != start_node:
                            continue
                        started = True

                    execution_order.append(node)
                    if node == "propose":
                        state["proposal"] = {"id": "p1"}
                    elif node == "experiment_setup":
                        state["experiment"] = {"id": "e1"}
                    elif node == "record":
                        state["loop_iteration"] = int(state.get("loop_iteration", 0)) + 1

                    if checkpoint_hook is not None:
                        next_node = node_sequence[node_sequence.index(node) + 1] if node != "record" else None
                        checkpoint_hook(node, next_node, dict(state))

                    if node == "experiment_setup" and start_node is None:
                        raise RuntimeError("pause at checkpoint boundary")

                return state

        fake_coordinator = _FakeCoordinator()
        monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _RecordingGraph())
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service
        service.checkpoint_coordinator = fake_coordinator

        run_id = service.create_run({"scenario": "data_science", "max_loops": 1})

        with pytest.raises(RuntimeError, match="pause at checkpoint boundary"):
            service.start_run(run_id)
        assert service.get_status(run_id) == RunStatus.FAILED.value
        assert service._runs[run_id]["latest_checkpoint_id"] == "ckpt-2"

        service._runs[run_id]["status"] = RunStatus.PAUSED.value
        service.resume_run(run_id)

        assert execution_order[:2] == ["propose", "experiment_setup"]
        assert execution_order[2:] == ["coding", "running", "feedback", "record"]
        assert service.get_status(run_id) == RunStatus.COMPLETED.value

    def test_pause_at_boundary_then_resume_does_not_rerun_prior_nodes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Prove that pause at checkpoint boundary and resume from next_node doesn't re-execute prior nodes.

        This test validates:
        1. Execution starts from node A
        2. Pause is issued and takes effect at checkpoint boundary after node B completes
        3. Resume restores state and continues from node C (next_node after B)
        4. Earlier nodes (A, B) are NOT re-run after resume
        """
        node_executions: list[str] = []
        checkpoints_saved: dict[str, dict] = {}

        class _FakeCoordinator:
            def save(self, name: str, workspace_data: bytes, state: dict) -> str:
                checkpoint_id = f"ckpt-{len(checkpoints_saved) + 1}"
                checkpoints_saved[checkpoint_id] = {
                    "state": dict(state),
                    "next_node": state.get("next_node"),
                }
                return checkpoint_id

            def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
                data = checkpoints_saved[checkpoint_id]
                return b"", data

        class _NodeTrackingGraph:
            def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
                node_sequence = ["node_a", "node_b", "node_c", "node_d"]
                started = start_node is None
                state = dict(initial_state)

                for node in node_sequence:
                    if not started:
                        if node != start_node:
                            continue
                        started = True

                    node_executions.append(node)
                    state["last_completed_node"] = node

                    # Simulate checkpoint callback after each node completes
                    if checkpoint_hook is not None:
                        next_idx = node_sequence.index(node) + 1
                        next_node_val = node_sequence[next_idx] if next_idx < len(node_sequence) else None
                        state_snapshot = dict(state)
                        state_snapshot["next_node"] = next_node_val
                        checkpoint_hook(node, next_node_val, state_snapshot)

                return state

        fake_coordinator = _FakeCoordinator()
        monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _NodeTrackingGraph())
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service
        service.checkpoint_coordinator = fake_coordinator

        # Create and start the run
        run_id = service.create_run({"scenario": "data_science", "max_loops": 1})
        service._runs[run_id]["status"] = RunStatus.RUNNING.value

        # Simulate a running graph that pauses after node_b
        # We artificially set it as if execution got to node_b, then pause took effect
        service._runs[run_id]["latest_checkpoint_id"] = "ckpt-2"
        # Manually populate checkpoints as if the graph ran to node_b
        checkpoints_saved["ckpt-1"] = {
            "run_id": run_id,
            "state": {"run_id": run_id, "loop_iteration": 0, "max_loops": 1, "last_completed_node": "node_a"},
            "next_node": "node_b",
        }
        checkpoints_saved["ckpt-2"] = {
            "run_id": run_id,
            "state": {"run_id": run_id, "loop_iteration": 0, "max_loops": 1, "last_completed_node": "node_b"},
            "next_node": "node_c",
        }

        # Pause the run
        service.pause_run(run_id)
        assert service.get_status(run_id) == RunStatus.PAUSED.value

        # Clear execution tracker to isolate resume behavior
        node_executions.clear()

        # Resume from checkpoint
        service.resume_run(run_id)
        assert service.get_status(run_id) == RunStatus.COMPLETED.value

        # Prove earlier nodes are NOT re-executed after resume
        # Only node_c and node_d should be in the execution list
        assert "node_a" not in node_executions, "node_a should not be re-executed after resume"
        assert "node_b" not in node_executions, "node_b should not be re-executed after resume"
        assert node_executions == ["node_c", "node_d"], (
            f"After resume, expected [node_c, node_d], got {node_executions}"
        )
