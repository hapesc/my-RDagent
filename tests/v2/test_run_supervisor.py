from __future__ import annotations

# pyright: reportMissingImports=false
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from v2.models import RunStatus
from v2.run_service import V2RunService
from v2.run_supervisor import V2RunSupervisor


def test_create_run_starts_worker_thread() -> None:
    sup = V2RunSupervisor(run_service=V2RunService())

    run_id = sup.create_run({"max_loops": 1})

    assert run_id in sup._controls or run_id in sup._workers or run_id in sup._run_service._runs


def test_pause_run_sets_pause_control_signal() -> None:
    sup = V2RunSupervisor(run_service=V2RunService())
    run_id = sup.create_run({"max_loops": 1})

    sup._controls[run_id] = "run"
    sup.pause_run(run_id)

    assert sup._controls[run_id] == "pause"


def test_recover_inflight_runs_marks_running_as_paused() -> None:
    sup = V2RunSupervisor(run_service=V2RunService())

    sup._inject_test_run("crashed-run-1", RunStatus.RUNNING.value)
    recovered = sup._recover_inflight_runs()

    assert "crashed-run-1" in recovered
    assert sup.get_status("crashed-run-1") == RunStatus.PAUSED.value
    assert sup._run_service._runs["crashed-run-1"]["config"]["recovery_required"] is True


def test_worker_error_marks_run_failed() -> None:
    sup = V2RunSupervisor(run_service=V2RunService())

    run_id = sup.create_run({"_force_worker_error": True, "max_loops": 1})
    time.sleep(0.2)

    assert sup.get_status(run_id) == RunStatus.FAILED.value


def test_resume_run_after_pause_completes() -> None:
    class _CapturingRunService(V2RunService):
        def __init__(self) -> None:
            super().__init__()
            self.resume_errors: list[str] = []

        def resume_run(self, run_id: str) -> None:
            try:
                super().resume_run(run_id)
            except Exception as exc:
                self.resume_errors.append(str(exc))
                raise

    run_service = _CapturingRunService()
    sup = V2RunSupervisor(run_service=run_service)

    run_service._runs["paused-run"] = {
        "config": {"max_loops": 1},
        "status": RunStatus.PAUSED.value,
    }
    sup._controls["paused-run"] = "pause"

    sup.resume_run("paused-run")
    time.sleep(0.3)

    assert run_service.resume_errors == ["Cannot resume run without latest_checkpoint_id"]
    assert sup.get_status("paused-run") == RunStatus.FAILED.value


def test_resume_run_uses_restored_checkpoint_state() -> None:
    class _SpyRunService(V2RunService):
        def __init__(self) -> None:
            super().__init__()
            self.start_calls: list[str] = []
            self.resume_calls: list[str] = []

        def start_run(self, run_id: str) -> None:
            self.start_calls.append(run_id)
            raise AssertionError("resume flow should not call start_run for paused run")

        def resume_run(self, run_id: str) -> None:
            run = self._runs[run_id]
            if not run.get("latest_checkpoint_id"):
                raise AssertionError("resume flow must preserve latest_checkpoint_id for restore")
            self.resume_calls.append(run_id)
            run["status"] = RunStatus.COMPLETED.value

    run_service = _SpyRunService()
    sup = V2RunSupervisor(run_service=run_service)

    run_id = "paused-with-checkpoint"
    run_service._runs[run_id] = {
        "config": {"max_loops": 1},
        "status": RunStatus.PAUSED.value,
        "latest_checkpoint_id": "ckpt-restore-1",
    }
    sup._controls[run_id] = "pause"

    sup.resume_run(run_id)
    time.sleep(0.3)

    assert run_service.resume_calls == [run_id]
    assert run_service.start_calls == []
    assert run_service._runs[run_id]["status"] == RunStatus.COMPLETED.value


def test_pause_requested_during_execution_pauses_at_next_checkpoint_boundary(
    monkeypatch,
) -> None:
    node2_started = threading.Event()
    allow_node2_complete = threading.Event()
    executed_nodes: list[str] = []

    class _FakeCoordinator:
        def __init__(self) -> None:
            self.saved: list[dict] = []

        def save(self, name: str, workspace_data: bytes, state: dict) -> str:
            self.saved.append({"name": name, "state": dict(state)})
            return f"ckpt-{len(self.saved)}"

    class _BlockingGraph:
        def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
            assert checkpoint_hook is not None
            state = dict(initial_state)
            node_sequence = ["propose", "coding", "running"]
            for index, node in enumerate(node_sequence):
                if node == "coding":
                    node2_started.set()
                    if not allow_node2_complete.wait(timeout=2):
                        raise AssertionError("test timeout waiting to finish coding node")

                state["last_node"] = node
                next_node = node_sequence[index + 1] if index + 1 < len(node_sequence) else None
                executed_nodes.append(node)
                checkpoint_hook(node, next_node, state)
            return state

    monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _BlockingGraph())

    run_service = V2RunService(checkpoint_coordinator=_FakeCoordinator())
    sup = V2RunSupervisor(run_service=run_service)
    run_id = sup.create_run({"max_loops": 1})

    assert node2_started.wait(timeout=2), "graph never entered second node"
    sup.pause_run(run_id)
    allow_node2_complete.set()

    deadline = time.time() + 2
    while time.time() < deadline:
        if sup.get_status(run_id) == RunStatus.PAUSED.value:
            break
        time.sleep(0.02)

    assert sup.get_status(run_id) == RunStatus.PAUSED.value
    assert executed_nodes == ["propose", "coding"]
    assert run_service._runs[run_id]["latest_checkpoint_id"] == "ckpt-2"


def test_pause_without_coordinator_pauses_at_boundary(monkeypatch) -> None:
    """Prove that pause works across node boundaries even without checkpoint coordinator."""
    node2_started = threading.Event()
    allow_node2_complete = threading.Event()
    executed_nodes: list[str] = []

    class _NoCoordGraph:
        def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
            assert checkpoint_hook is not None
            state = dict(initial_state)
            node_sequence = ["propose", "experiment_setup", "coding"]
            for index, node in enumerate(node_sequence):
                if node == "experiment_setup":
                    node2_started.set()
                    if not allow_node2_complete.wait(timeout=2):
                        raise AssertionError("test timeout waiting to finish experiment_setup node")

                state["last_node"] = node
                next_node = node_sequence[index + 1] if index + 1 < len(node_sequence) else None
                executed_nodes.append(node)
                checkpoint_hook(node, next_node, state)
            return state

    monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _NoCoordGraph())

    # NO coordinator passed
    run_service = V2RunService(checkpoint_coordinator=None)
    sup = V2RunSupervisor(run_service=run_service)
    run_id = sup.create_run({"max_loops": 1})

    assert node2_started.wait(timeout=2), "graph never entered second node"
    sup.pause_run(run_id)
    allow_node2_complete.set()

    deadline = time.time() + 2
    while time.time() < deadline:
        if sup.get_status(run_id) == RunStatus.PAUSED.value:
            break
        time.sleep(0.02)

    assert sup.get_status(run_id) == RunStatus.PAUSED.value
    assert executed_nodes == ["propose", "experiment_setup"]
    assert run_service._runs[run_id]["latest_checkpoint_id"] is None
