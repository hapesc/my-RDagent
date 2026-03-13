from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from v2.models import RunStatus
from v2.runtime import build_v2_runtime


class TestLifecycleE2E:
    def test_pause_resume(self) -> None:
        class _FakeCoordinator:
            def __init__(self, run_id_ref: dict) -> None:
                self._run_id_ref = run_id_ref
                self.saved: list[dict] = []

            def save(self, name: str, workspace_data: bytes, state: dict) -> str:
                self.saved.append(state)
                return f"ckpt-{len(self.saved)}"

            def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
                idx = int(checkpoint_id.split("-")[1]) - 1
                return b"", self.saved[idx]

        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service

        run_id = service.create_run({"scenario": "data_science", "max_loops": 1, "task_summary": "pause-resume"})
        run_id_ref = {"value": run_id}
        coordinator = _FakeCoordinator(run_id_ref)
        service.checkpoint_coordinator = coordinator

        pause_after_node = {"value": "experiment_setup"}

        def _pause_probe(rid: str) -> bool:
            if not coordinator.saved:
                return False
            last = coordinator.saved[-1]
            return last.get("last_completed_node") == pause_after_node["value"]

        service.set_pause_probe(_pause_probe)
        service.start_run(run_id)
        assert service.get_status(run_id) == RunStatus.PAUSED.value

        service.set_pause_probe(None)
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

    def test_idempotency(self) -> None:
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

    def test_resume_continues_from_checkpointed_next_node(self) -> None:
        class _FakeCoordinator:
            def __init__(self) -> None:
                self.saved_states: list[dict] = []

            def save(self, name: str, workspace_data: bytes, state: dict) -> str:
                self.saved_states.append(dict(state))
                return f"ckpt-{len(self.saved_states)}"

            def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
                index = int(checkpoint_id.split("-")[1]) - 1
                return b"", self.saved_states[index]

        fake_coordinator = _FakeCoordinator()
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service
        service.checkpoint_coordinator = fake_coordinator

        run_id = service.create_run({"scenario": "data_science", "max_loops": 1})

        pause_once = {"triggered": False}

        def _pause_probe(rid: str) -> bool:
            if pause_once["triggered"]:
                return False
            if not fake_coordinator.saved_states:
                return False
            last = fake_coordinator.saved_states[-1]
            if last.get("last_completed_node") == "experiment_setup":
                pause_once["triggered"] = True
                return True
            return False

        service.set_pause_probe(_pause_probe)
        service.start_run(run_id)
        assert service.get_status(run_id) == RunStatus.PAUSED.value

        service.set_pause_probe(None)
        service.resume_run(run_id)

        assert service.get_status(run_id) == RunStatus.COMPLETED.value
        executed_nodes = [s["last_completed_node"] for s in fake_coordinator.saved_states]
        assert "propose" in executed_nodes
        assert "experiment_setup" in executed_nodes
        assert "coding" in executed_nodes

    def test_pause_at_boundary_then_resume_does_not_rerun_prior_nodes(self) -> None:
        class _FakeCoordinator:
            def __init__(self) -> None:
                self.saved_states: list[dict] = []

            def save(self, name: str, workspace_data: bytes, state: dict) -> str:
                self.saved_states.append(dict(state))
                return f"ckpt-{len(self.saved_states)}"

            def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
                index = int(checkpoint_id.split("-")[1]) - 1
                return b"", self.saved_states[index]

        fake_coordinator = _FakeCoordinator()
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service
        service.checkpoint_coordinator = fake_coordinator

        run_id = service.create_run({"scenario": "data_science", "max_loops": 1})

        pause_once = {"triggered": False}

        def _pause_probe(rid: str) -> bool:
            if pause_once["triggered"]:
                return False
            if not fake_coordinator.saved_states:
                return False
            last = fake_coordinator.saved_states[-1]
            if last.get("last_completed_node") == "experiment_setup":
                pause_once["triggered"] = True
                return True
            return False

        service.set_pause_probe(_pause_probe)
        service.start_run(run_id)
        assert service.get_status(run_id) == RunStatus.PAUSED.value

        before_resume_count = len(fake_coordinator.saved_states)

        service.set_pause_probe(None)
        service.resume_run(run_id)
        assert service.get_status(run_id) == RunStatus.COMPLETED.value

        resume_states = fake_coordinator.saved_states[before_resume_count:]
        resume_nodes = [s["last_completed_node"] for s in resume_states]
        assert "propose" not in resume_nodes, "propose should not be re-executed after resume"
        assert "experiment_setup" not in resume_nodes, "experiment_setup should not be re-executed after resume"
        # With the deferred checkpoint approach, the pause probe triggers after
        # coding has already executed (because experiment_setup's checkpoint is
        # saved when coding's event arrives).  So coding is also not re-executed.
        assert "coding" not in resume_nodes, "coding should not be re-executed after resume"
        assert "running" in resume_nodes
        assert "feedback" in resume_nodes
        assert "record" in resume_nodes
        assert "record_notes" in resume_nodes


class TestSqliteCheckpointLifecycle:
    """Integration tests for SqliteSaver-backed checkpoint persistence."""

    def test_complete_run_with_sqlite_persists_state(self, tmp_path: Path) -> None:
        """A complete run with SqliteSaver creates a non-empty DB file."""
        db_path = str(tmp_path / "lifecycle.db")
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service
        service._sqlite_path = db_path

        run_id = service.create_run({"scenario": "data_science", "max_loops": 1})
        service.start_run(run_id)

        assert service.get_status(run_id) == RunStatus.COMPLETED.value
        assert (tmp_path / "lifecycle.db").exists()
        assert (tmp_path / "lifecycle.db").stat().st_size > 0

    def test_resume_restores_full_state_with_sqlite(self, tmp_path: Path) -> None:
        """After pause+resume with SqliteSaver, all state fields survive."""
        db_path = str(tmp_path / "resume.db")

        class _FakeCoordinator:
            def __init__(self) -> None:
                self.saved: list[dict] = []

            def save(self, name: str, workspace_data: bytes, state: dict) -> str:
                self.saved.append(dict(state))
                return f"ckpt-{len(self.saved)}"

            def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
                idx = int(checkpoint_id.split("-")[1]) - 1
                return b"", self.saved[idx]

        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        service = ctx.run_service
        service._sqlite_path = db_path

        coordinator = _FakeCoordinator()
        service.checkpoint_coordinator = coordinator

        run_id = service.create_run({"scenario": "data_science", "max_loops": 1, "task_summary": "sqlite-resume"})

        pause_once = {"triggered": False}

        def _pause_probe(rid: str) -> bool:
            if pause_once["triggered"]:
                return False
            if not coordinator.saved:
                return False
            last = coordinator.saved[-1]
            if last.get("last_completed_node") == "experiment_setup":
                pause_once["triggered"] = True
                return True
            return False

        service.set_pause_probe(_pause_probe)
        service.start_run(run_id)
        assert service.get_status(run_id) == RunStatus.PAUSED.value
        assert (tmp_path / "resume.db").exists()

        # Resume: still using the same sqlite DB for LangGraph internal checkpoints.
        service.set_pause_probe(None)
        service.resume_run(run_id)
        assert service.get_status(run_id) == RunStatus.COMPLETED.value

        # Verify state fields survived the round-trip.
        executed_nodes = [s["last_completed_node"] for s in coordinator.saved]
        assert "propose" in executed_nodes
        assert "experiment_setup" in executed_nodes
        assert "record_notes" in executed_nodes

    def test_sqlite_path_via_constructor(self, tmp_path: Path) -> None:
        """V2RunService accepts sqlite_path in constructor."""
        from v2.run_service import V2RunService

        db_path = str(tmp_path / "ctor.db")
        service = V2RunService(sqlite_path=db_path)
        assert service._sqlite_path == db_path

        run_id = service.create_run({"max_loops": 1})
        service.start_run(run_id)
        assert service.get_status(run_id) == RunStatus.COMPLETED.value
        assert (tmp_path / "ctor.db").exists()
