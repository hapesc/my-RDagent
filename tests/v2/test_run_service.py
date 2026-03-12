from __future__ import annotations

# pyright: reportMissingImports=false

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from v2.models import RunStatus
from v2.run_service import V2RunService


def test_create_then_start_run_completes_with_graph_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    service = V2RunService()
    invoked_with: list[dict] = []

    class _DummyGraph:
        def invoke(self, initial_state: dict) -> dict:
            invoked_with.append(dict(initial_state))
            return dict(initial_state)

    monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _DummyGraph())

    run_id = service.create_run({"max_loops": 2})
    service.start_run(run_id)

    assert invoked_with == [{"run_id": run_id, "loop_iteration": 0, "max_loops": 2}]
    assert service.get_status(run_id) == RunStatus.COMPLETED.value


def test_pause_non_running_raises_value_error() -> None:
    service = V2RunService()
    run_id = service.create_run({})

    with pytest.raises(ValueError, match="Cannot pause run"):
        service.pause_run(run_id)


def test_fork_run_creates_new_run_id_with_created_status() -> None:
    service = V2RunService()
    run_id = service.create_run({"max_loops": 3})

    forked_run_id = service.fork_run(run_id)

    assert forked_run_id != run_id
    assert service.get_status(forked_run_id) == RunStatus.CREATED.value


def test_get_status_returns_current_status() -> None:
    service = V2RunService()
    run_id = service.create_run({})

    assert service.get_status(run_id) == RunStatus.CREATED.value
