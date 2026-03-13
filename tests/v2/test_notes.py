from __future__ import annotations

import json
from pathlib import Path

from v2.graph.notes import record_notes_node, retrieve_notes_from_file


def test_record_notes_writes_run_state_json(tmp_path: Path) -> None:
    state = {
        "run_id": "test-run",
        "loop_iteration": 2,
        "max_loops": 5,
        "step_state": "COMPLETED",
        "proposal": {"hypothesis": "test hypothesis"},
        "experiment": None,
        "code_result": None,
        "run_result": None,
        "feedback": {"score": 0.8},
        "metrics": [{"iteration": 1, "score": 0.7}],
        "error": None,
        "tokens_used": 500,
        "token_budget": 10000,
        "iteration_history": [{"iteration": 1, "score": 0.7}],
        "context_notes": None,
        "workspace_path": str(tmp_path),
    }

    result = record_notes_node(state)

    assert result == {}
    run_state_path = tmp_path / "RUN_STATE.json"
    assert run_state_path.exists()
    data = json.loads(run_state_path.read_text())
    assert data["run_id"] == "test-run"
    assert data["loop_iteration"] == 2
    assert data["tokens_used"] == 500


def test_record_notes_skips_when_no_workspace() -> None:
    state = {
        "run_id": "test-run",
        "loop_iteration": 1,
        "max_loops": 3,
        "step_state": "COMPLETED",
        "proposal": None,
        "experiment": None,
        "code_result": None,
        "run_result": None,
        "feedback": None,
        "metrics": None,
        "error": None,
        "tokens_used": 0,
        "token_budget": 0,
        "iteration_history": [],
        "context_notes": None,
        "workspace_path": None,
    }

    result = record_notes_node(state)

    assert result == {}


def test_retrieve_notes_reads_existing_file(tmp_path: Path) -> None:
    run_state = {"run_id": "existing-run", "loop_iteration": 3}
    (tmp_path / "RUN_STATE.json").write_text(json.dumps(run_state))

    result = retrieve_notes_from_file(str(tmp_path))

    assert result == run_state


def test_retrieve_notes_returns_empty_when_no_file(tmp_path: Path) -> None:
    result = retrieve_notes_from_file(str(tmp_path))

    assert result == {}
