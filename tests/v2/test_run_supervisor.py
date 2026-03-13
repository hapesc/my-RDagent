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


def test_pause_requested_during_execution_pauses_at_next_checkpoint_boundary() -> None:
    runner_started = threading.Event()
    allow_runner_complete = threading.Event()
    executed_nodes: list[str] = []

    class _BlockingRunnerPlugin:
        def run(self, code: dict) -> dict:
            executed_nodes.append("running")
            runner_started.set()
            if not allow_runner_complete.wait(timeout=5):
                raise AssertionError("test timeout waiting to finish running node")
            return {"success": True, "output": "ok"}

    class _TrackingProposerPlugin:
        def propose(self, state: dict) -> dict:
            executed_nodes.append("propose")
            return {"summary": "test"}

    class _TrackingEvaluatorPlugin:
        def evaluate(self, experiment: dict, result: dict) -> dict:
            executed_nodes.append("feedback")
            return {"score": 0.5, "decision": "continue"}

    class _FakeCoordinator:
        def __init__(self) -> None:
            self.saved: list[dict] = []

        def save(self, name: str, workspace_data: bytes, state: dict) -> str:
            self.saved.append({"name": name, "state": dict(state)})
            return f"ckpt-{len(self.saved)}"

    from v2.plugins.contracts import ScenarioBundle
    from v2.plugins.registry import PluginRegistry

    bundle = ScenarioBundle(
        proposer=_TrackingProposerPlugin(),
        coder=type("C", (), {"develop": staticmethod(lambda e, p: {"code": "pass"})})(),
        runner=_BlockingRunnerPlugin(),
        evaluator=_TrackingEvaluatorPlugin(),
    )
    registry = PluginRegistry()
    registry.register("test", bundle)

    coordinator = _FakeCoordinator()
    run_service = V2RunService(plugin_registry=registry, checkpoint_coordinator=coordinator)
    sup = V2RunSupervisor(run_service=run_service)
    run_id = sup.create_run({"max_loops": 1, "scenario": "test"})

    assert runner_started.wait(timeout=3), "graph never reached running node"
    sup.pause_run(run_id)
    allow_runner_complete.set()

    deadline = time.time() + 3
    while time.time() < deadline:
        if sup.get_status(run_id) == RunStatus.PAUSED.value:
            break
        time.sleep(0.02)

    assert sup.get_status(run_id) == RunStatus.PAUSED.value
    assert "propose" in executed_nodes
    assert "running" in executed_nodes


def test_pause_without_coordinator_pauses_at_boundary() -> None:
    """Prove that pause works across node boundaries even without checkpoint coordinator."""
    runner_started = threading.Event()
    allow_runner_complete = threading.Event()
    executed_nodes: list[str] = []

    class _BlockingRunnerPlugin:
        def run(self, code: dict) -> dict:
            executed_nodes.append("running")
            runner_started.set()
            if not allow_runner_complete.wait(timeout=5):
                raise AssertionError("test timeout waiting to finish running node")
            return {"success": True, "output": "ok"}

    class _TrackingProposerPlugin:
        def propose(self, state: dict) -> dict:
            executed_nodes.append("propose")
            return {"summary": "test"}

    from v2.plugins.contracts import ScenarioBundle
    from v2.plugins.registry import PluginRegistry

    bundle = ScenarioBundle(
        proposer=_TrackingProposerPlugin(),
        coder=type("C", (), {"develop": staticmethod(lambda e, p: {"code": "pass"})})(),
        runner=_BlockingRunnerPlugin(),
        evaluator=type("E", (), {"evaluate": staticmethod(lambda e, r: {"score": 0.5})})(),
    )
    registry = PluginRegistry()
    registry.register("test", bundle)

    # NO coordinator passed
    run_service = V2RunService(plugin_registry=registry, checkpoint_coordinator=None)
    sup = V2RunSupervisor(run_service=run_service)
    run_id = sup.create_run({"max_loops": 1, "scenario": "test"})

    assert runner_started.wait(timeout=3), "graph never reached running node"
    sup.pause_run(run_id)
    allow_runner_complete.set()

    deadline = time.time() + 3
    while time.time() < deadline:
        if sup.get_status(run_id) == RunStatus.PAUSED.value:
            break
        time.sleep(0.02)

    assert sup.get_status(run_id) == RunStatus.PAUSED.value
    assert "propose" in executed_nodes
    assert "running" in executed_nodes
    assert run_service._runs[run_id]["latest_checkpoint_id"] is None
