from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from v2.models import RunStatus
from v2.runtime import build_v2_runtime


class _DummyGraph:
    def invoke(self, initial_state: dict) -> dict:
        return dict(initial_state)


class TestLifecycleE2E:
    def test_pause_resume(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _DummyGraph())
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service

        run_id = service.create_run({"scenario": "data_science", "max_loops": 1})
        assert service.get_status(run_id) == RunStatus.CREATED.value

        service._runs[run_id]["status"] = RunStatus.RUNNING.value
        service.pause_run(run_id)
        assert service.get_status(run_id) == RunStatus.PAUSED.value

        service.resume_run(run_id)
        assert service.get_status(run_id) == RunStatus.COMPLETED.value

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
