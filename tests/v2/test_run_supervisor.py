from __future__ import annotations

# pyright: reportMissingImports=false

import sys
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
