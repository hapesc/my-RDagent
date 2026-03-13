from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RUN_STATE_FILENAME = "RUN_STATE.json"


def _build_run_state(state: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from the graph state for persistence."""
    return {
        "run_id": state.get("run_id"),
        "loop_iteration": state.get("loop_iteration"),
        "max_loops": state.get("max_loops"),
        "step_state": state.get("step_state"),
        "tokens_used": state.get("tokens_used"),
        "token_budget": state.get("token_budget"),
        "iteration_history": state.get("iteration_history", []),
        "error": state.get("error"),
    }


def record_notes_node(state: dict[str, Any]) -> dict[str, Any]:
    """Write a RUN_STATE.json snapshot to the workspace directory.

    Returns an empty dict (no state mutations) so that the graph state
    is not altered by this side-effect-only node.
    """
    workspace_path = state.get("workspace_path")
    if not workspace_path:
        return {}

    run_state = _build_run_state(state)
    out_path = Path(workspace_path) / RUN_STATE_FILENAME
    out_path.write_text(json.dumps(run_state, indent=2, default=str))
    return {}


def retrieve_notes_from_file(workspace_path: str) -> dict[str, Any]:
    """Read RUN_STATE.json from the workspace directory.

    Returns the parsed dict, or an empty dict if the file does not exist.
    """
    p = Path(workspace_path) / RUN_STATE_FILENAME
    if not p.exists():
        return {}
    try:
        return dict(json.loads(p.read_text()))
    except (json.JSONDecodeError, OSError):
        return {}


__all__ = ["record_notes_node", "retrieve_notes_from_file"]
