from __future__ import annotations

import sys
from pathlib import Path

import pytest

from v2.models import RunStatus
from v2.run_service import V2RunService

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_create_then_start_run_completes() -> None:
    service = V2RunService()

    run_id = service.create_run({"max_loops": 1})
    service.start_run(run_id)

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


def test_start_run_persists_node_boundary_checkpoint_payloads() -> None:
    saved_calls: list[dict] = []

    class _FakeCoordinator:
        def save(self, name: str, workspace_data: bytes, state: dict) -> str:
            saved_calls.append({"name": name, "workspace_data": workspace_data, "state": state})
            return f"ckpt-{len(saved_calls)}"

    service = V2RunService(checkpoint_coordinator=_FakeCoordinator())
    run_id = service.create_run({"max_loops": 1, "task_summary": "checkpoint me"})

    service.start_run(run_id)

    assert len(saved_calls) == 7
    first_payload = saved_calls[0]["state"]
    assert first_payload["run_id"] == run_id
    assert first_payload["last_completed_node"] == "propose"
    assert first_payload["next_node"] == "experiment_setup"
    assert first_payload["state"]["proposal"] is not None

    last_payload = saved_calls[-1]["state"]
    assert last_payload["last_completed_node"] == "record_notes"
    assert last_payload["next_node"] is None
    assert last_payload["state"]["loop_iteration"] == 1

    assert service._runs[run_id]["latest_checkpoint_id"] == f"ckpt-{len(saved_calls)}"


def test_resume_run_restores_checkpoint_and_continues_from_next_node() -> None:
    expected_run_id = {"value": "RUN-ID"}

    class _FakeCoordinator:
        def __init__(self) -> None:
            self.restored: list[str] = []
            self.saved: list[dict] = []

        def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
            self.restored.append(checkpoint_id)
            return (
                b"",
                {
                    "run_id": expected_run_id["value"],
                    "loop_iteration": 0,
                    "last_completed_node": "experiment_setup",
                    "next_node": "coding",
                    "state": {
                        "run_id": expected_run_id["value"],
                        "loop_iteration": 0,
                        "max_loops": 1,
                        "step_state": "CODING",
                        "proposal": {"id": "p1"},
                        "experiment": {"id": "e1"},
                        "code_result": None,
                        "run_result": None,
                        "feedback": None,
                        "metrics": None,
                        "error": None,
                        "tokens_used": 0,
                        "token_budget": 0,
                    },
                },
            )

        def save(self, name: str, workspace_data: bytes, state: dict) -> str:
            self.saved.append(state)
            return f"ckpt-{len(self.saved)}"

    coordinator = _FakeCoordinator()
    service = V2RunService(checkpoint_coordinator=coordinator)
    run_id = service.create_run({"max_loops": 1})
    expected_run_id["value"] = run_id
    service._runs[run_id]["status"] = RunStatus.PAUSED.value
    service._runs[run_id]["latest_checkpoint_id"] = "ckpt-42"

    service.resume_run(run_id)

    assert coordinator.restored == ["ckpt-42"]
    assert service.get_status(run_id) == RunStatus.COMPLETED.value
    assert len(coordinator.saved) >= 1
    executed_nodes = [s["last_completed_node"] for s in coordinator.saved]
    assert "propose" not in executed_nodes
    assert "experiment_setup" not in executed_nodes
    assert "coding" in executed_nodes


@pytest.mark.parametrize(
    ("payload", "checkpoint_id", "expected_error"),
    [
        (None, None, "Cannot resume run without latest_checkpoint_id"),
        (
            {
                "run_id": "mismatch-run-id",
                "loop_iteration": 1,
                "last_completed_node": "propose",
                "next_node": "coding",
                "state": {"run_id": "mismatch-run-id", "loop_iteration": 1},
            },
            "ckpt-1",
            "Invalid recovery payload: run_id mismatch",
        ),
        (
            {
                "run_id": "__USE_RUN_ID__",
                "loop_iteration": 1,
                "last_completed_node": "propose",
                "next_node": "coding",
            },
            "ckpt-2",
            "Invalid recovery payload: missing state",
        ),
        (
            {
                "run_id": "__USE_RUN_ID__",
                "loop_iteration": 1,
                "last_completed_node": "coding",
                "next_node": None,
                "state": {"run_id": "__USE_RUN_ID__", "loop_iteration": 1},
            },
            "ckpt-3",
            "Invalid recovery payload: next_node is None",
        ),
    ],
)
def test_resume_run_rejects_invalid_checkpoint_payload_without_executing_graph(
    payload: dict | None,
    checkpoint_id: str | None,
    expected_error: str,
) -> None:
    class _Coordinator:
        def __init__(self, restored_payload: dict | None) -> None:
            self._restored_payload = restored_payload

        def restore(self, _: str) -> tuple[bytes, dict]:
            assert self._restored_payload is not None
            return b"", dict(self._restored_payload)

    service = V2RunService(checkpoint_coordinator=_Coordinator(payload))
    run_id = service.create_run({"max_loops": 5})
    service._runs[run_id]["status"] = RunStatus.PAUSED.value
    service._runs[run_id]["latest_checkpoint_id"] = checkpoint_id

    if payload is not None:
        normalized_payload = dict(payload)
        if normalized_payload.get("run_id") == "__USE_RUN_ID__":
            normalized_payload["run_id"] = run_id
        state = normalized_payload.get("state")
        if isinstance(state, dict) and state.get("run_id") == "__USE_RUN_ID__":
            normalized_payload["state"] = {**state, "run_id": run_id}
        service.checkpoint_coordinator = _Coordinator(normalized_payload)

    with pytest.raises(ValueError, match=expected_error):
        service.resume_run(run_id)

    assert service.get_status(run_id) == RunStatus.FAILED.value


def test_resume_run_fails_when_checkpoint_restore_raises_and_does_not_execute_graph() -> None:
    class _BrokenCoordinator:
        def restore(self, _: str) -> tuple[bytes, dict]:
            raise RuntimeError("blob restore failed")

    service = V2RunService(checkpoint_coordinator=_BrokenCoordinator())
    run_id = service.create_run({"max_loops": 3})
    service._runs[run_id]["status"] = RunStatus.PAUSED.value
    service._runs[run_id]["latest_checkpoint_id"] = "ckpt-broken"

    with pytest.raises(ValueError, match="Failed to restore checkpoint"):
        service.resume_run(run_id)

    assert service.get_status(run_id) == RunStatus.FAILED.value


def test_start_run_uses_sqlite_checkpointer_when_path_provided(tmp_path: Path) -> None:
    """When sqlite_path is a real file, SqliteSaver is used for persistence."""
    db_path = str(tmp_path / "checkpoints.db")
    service = V2RunService(sqlite_path=db_path)
    run_id = service.create_run({"max_loops": 1})
    service.start_run(run_id)
    assert service.get_status(run_id) == RunStatus.COMPLETED.value
    assert (tmp_path / "checkpoints.db").exists()


def test_sqlite_checkpointer_creates_db_file_on_disk(tmp_path: Path) -> None:
    """SqliteSaver creates a real SQLite database file that is non-empty."""
    db_path = str(tmp_path / "ckpt.sqlite3")
    service = V2RunService(sqlite_path=db_path)
    run_id = service.create_run({"max_loops": 1})
    service.start_run(run_id)

    db_file = tmp_path / "ckpt.sqlite3"
    assert db_file.exists()
    assert db_file.stat().st_size > 0


def test_sqlite_checkpointer_default_is_memory() -> None:
    """Without sqlite_path, the service defaults to in-memory MemorySaver."""
    service = V2RunService()
    assert service._sqlite_path == ":memory:"
    run_id = service.create_run({"max_loops": 1})
    service.start_run(run_id)
    assert service.get_status(run_id) == RunStatus.COMPLETED.value


def test_existing_tests_unaffected_by_sqlite_path_parameter() -> None:
    """Passing no sqlite_path still works exactly like before."""
    service = V2RunService()
    run_id = service.create_run({"max_loops": 1})
    service.start_run(run_id)
    assert service.get_status(run_id) == RunStatus.COMPLETED.value


def test_resume_integrity_check_rejects_mismatched_next_node() -> None:
    """If the checkpoint's next_node doesn't match what the graph actually executes, raise."""

    class _MismatchCoordinator:
        def __init__(self, run_id_ref: dict) -> None:
            self._run_id_ref = run_id_ref

        def restore(self, _: str) -> tuple[bytes, dict]:
            return (
                b"",
                {
                    "run_id": self._run_id_ref["value"],
                    "loop_iteration": 0,
                    "last_completed_node": "experiment_setup",
                    # Deliberately wrong: real successor of experiment_setup is "coding"
                    "next_node": "running",
                    "state": {
                        "run_id": self._run_id_ref["value"],
                        "loop_iteration": 0,
                        "max_loops": 1,
                        "step_state": "CODING",
                        "proposal": {"id": "p1"},
                        "experiment": {"id": "e1"},
                        "code_result": None,
                        "run_result": None,
                        "feedback": None,
                        "metrics": None,
                        "error": None,
                        "tokens_used": 0,
                        "token_budget": 0,
                    },
                },
            )

        def save(self, name: str, workspace_data: bytes, state: dict) -> str:
            return "ckpt-fake"

    run_id_ref: dict = {"value": ""}
    coordinator = _MismatchCoordinator(run_id_ref)
    service = V2RunService(checkpoint_coordinator=coordinator)
    run_id = service.create_run({"max_loops": 1})
    run_id_ref["value"] = run_id
    service._runs[run_id]["status"] = RunStatus.PAUSED.value
    service._runs[run_id]["latest_checkpoint_id"] = "ckpt-42"

    with pytest.raises(ValueError, match="Resume integrity check failed"):
        service.resume_run(run_id)

    assert service.get_status(run_id) == RunStatus.FAILED.value


def test_get_run_payload_exposes_benchmark_consumable_snapshot() -> None:
    service = V2RunService(runtime_metadata={"llm_provider": "litellm", "llm_model": "gpt-4.1-mini"})
    run_id = service.create_run({"scenario": "data_science", "max_loops": 1, "task_summary": "payload"})

    service.start_run(run_id)

    payload = service.get_run_payload(run_id)
    assert payload is not None
    assert payload["run_id"] == run_id
    assert payload["scenario"] == "data_science"
    assert payload["status"] == RunStatus.COMPLETED.value
    assert "final_state" in payload
    assert "artifacts" in payload
    assert "runtime" in payload
    assert payload["runtime"]["llm_provider"] == "litellm"
    assert payload["runtime"]["llm_model"] == "gpt-4.1-mini"


def test_get_run_payload_updates_after_resume() -> None:
    class _FakeCoordinator:
        def __init__(self) -> None:
            self.saved: list[dict] = []

        def save(self, name: str, workspace_data: bytes, state: dict) -> str:
            _ = (name, workspace_data)
            self.saved.append(dict(state))
            return f"ckpt-{len(self.saved)}"

        def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
            idx = int(checkpoint_id.split("-")[1]) - 1
            return b"", self.saved[idx]

    coordinator = _FakeCoordinator()
    service = V2RunService(
        checkpoint_coordinator=coordinator,
        runtime_metadata={"llm_provider": "mock", "llm_model": "mock-model"},
    )
    run_id = service.create_run({"scenario": "data_science", "max_loops": 1, "task_summary": "resume-payload"})

    def _pause_probe(_: str) -> bool:
        return bool(coordinator.saved) and coordinator.saved[-1].get("last_completed_node") == "experiment_setup"

    service.set_pause_probe(_pause_probe)
    service.start_run(run_id)
    paused_payload = service.get_run_payload(run_id)
    assert paused_payload is not None
    assert paused_payload["status"] == RunStatus.PAUSED.value

    service.set_pause_probe(None)
    service.resume_run(run_id)
    resumed_payload = service.get_run_payload(run_id)
    assert resumed_payload is not None
    assert resumed_payload["status"] == RunStatus.COMPLETED.value
