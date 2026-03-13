from __future__ import annotations

# pyright: reportMissingImports=false
import sys
from pathlib import Path

import pytest

from v2.models import RunStatus
from v2.run_service import V2RunService

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_create_then_start_run_completes_with_graph_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    service = V2RunService()
    invoked_with: list[dict] = []

    class _DummyGraph:
        def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
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


def test_start_run_persists_node_boundary_checkpoint_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    saved_calls: list[dict] = []

    class _FakeCoordinator:
        def save(self, name: str, workspace_data: bytes, state: dict) -> str:
            saved_calls.append({"name": name, "workspace_data": workspace_data, "state": state})
            return f"ckpt-{len(saved_calls)}"

    class _DummyGraph:
        def invoke(self, initial_state: dict, checkpoint_hook=None) -> dict:
            assert checkpoint_hook is not None
            state_after_propose = dict(initial_state)
            state_after_propose["proposal"] = {"title": "p1"}
            checkpoint_hook("propose", "coding", state_after_propose)

            state_after_coding = dict(state_after_propose)
            state_after_coding["loop_iteration"] = 1
            checkpoint_hook("coding", None, state_after_coding)
            return state_after_coding

    monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _DummyGraph())

    service = V2RunService(checkpoint_coordinator=_FakeCoordinator())
    run_id = service.create_run({"max_loops": 1, "task_summary": "checkpoint me"})

    service.start_run(run_id)

    assert len(saved_calls) == 2
    first_payload = saved_calls[0]["state"]
    assert first_payload["run_id"] == run_id
    assert first_payload["loop_iteration"] == 0
    assert first_payload["last_completed_node"] == "propose"
    assert first_payload["next_node"] == "coding"
    assert first_payload["state"]["proposal"] == {"title": "p1"}

    second_payload = saved_calls[1]["state"]
    assert second_payload["run_id"] == run_id
    assert second_payload["loop_iteration"] == 1
    assert second_payload["last_completed_node"] == "coding"
    assert second_payload["next_node"] is None
    assert second_payload["state"]["loop_iteration"] == 1

    assert service._runs[run_id]["latest_checkpoint_id"] == "ckpt-2"


def test_resume_run_restores_checkpoint_and_continues_from_next_node(monkeypatch: pytest.MonkeyPatch) -> None:
    restored_calls: list[str] = []
    invoke_calls: list[dict] = []
    expected_run_id = {"value": "RUN-ID"}

    class _FakeCoordinator:
        def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
            restored_calls.append(checkpoint_id)
            return (
                b"",
                {
                    "run_id": expected_run_id["value"],
                    "loop_iteration": 7,
                    "last_completed_node": "experiment_setup",
                    "next_node": "coding",
                    "state": {
                        "run_id": expected_run_id["value"],
                        "loop_iteration": 7,
                        "max_loops": 10,
                        "task_summary": "resume here",
                        "proposal": {"id": "p1"},
                        "experiment": {"id": "e1"},
                    },
                },
            )

    class _DummyGraph:
        def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
            invoke_calls.append(
                {
                    "initial_state": dict(initial_state),
                    "start_node": start_node,
                    "checkpoint_hook": checkpoint_hook,
                }
            )
            return dict(initial_state)

    monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _DummyGraph())

    service = V2RunService(checkpoint_coordinator=_FakeCoordinator())
    run_id = service.create_run({"max_loops": 10, "task_summary": "resume here"})
    expected_run_id["value"] = run_id
    service._runs[run_id]["status"] = RunStatus.PAUSED.value
    service._runs[run_id]["latest_checkpoint_id"] = "ckpt-42"
    service._runs[run_id]["config"]["task_summary"] = "ignored after restore"
    service._runs[run_id]["config"]["max_loops"] = 1

    service.resume_run(run_id)

    assert restored_calls == ["ckpt-42"]
    assert invoke_calls[0]["start_node"] == "coding"
    assert invoke_calls[0]["initial_state"]["run_id"] == run_id
    assert invoke_calls[0]["initial_state"]["loop_iteration"] == 7
    assert invoke_calls[0]["initial_state"]["max_loops"] == 10
    assert invoke_calls[0]["initial_state"]["proposal"] == {"id": "p1"}
    assert service.get_status(run_id) == RunStatus.COMPLETED.value


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
    monkeypatch: pytest.MonkeyPatch,
    payload: dict | None,
    checkpoint_id: str | None,
    expected_error: str,
) -> None:
    graph_invoked = {"value": False}

    class _DummyGraph:
        def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
            graph_invoked["value"] = True
            return dict(initial_state)

    monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _DummyGraph())

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
    assert graph_invoked["value"] is False


def test_resume_run_fails_when_checkpoint_restore_raises_and_does_not_execute_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_invoked = {"value": False}

    class _DummyGraph:
        def invoke(self, initial_state: dict, start_node: str | None = None, checkpoint_hook=None) -> dict:
            graph_invoked["value"] = True
            return dict(initial_state)

    class _BrokenCoordinator:
        def restore(self, _: str) -> tuple[bytes, dict]:
            raise RuntimeError("blob restore failed")

    monkeypatch.setattr("v2.run_service.build_main_graph", lambda: _DummyGraph())

    service = V2RunService(checkpoint_coordinator=_BrokenCoordinator())
    run_id = service.create_run({"max_loops": 3})
    service._runs[run_id]["status"] = RunStatus.PAUSED.value
    service._runs[run_id]["latest_checkpoint_id"] = "ckpt-broken"

    with pytest.raises(ValueError, match="Failed to restore checkpoint"):
        service.resume_run(run_id)

    assert service.get_status(run_id) == RunStatus.FAILED.value
    assert graph_invoked["value"] is False
