"""Branch-facing V3 tool handlers."""

from __future__ import annotations

from typing import Any

from rd_agent.contracts.branch import BranchStatus
from rd_agent.contracts.tool_io import BranchGetRequest, BranchGetResult, BranchListRequest, BranchListResult
from rd_agent.ports.state_store import StateStorePort


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_branch_get(request: BranchGetRequest, *, state_store: StateStorePort) -> dict[str, Any]:
    branch = state_store.load_branch_snapshot(request.branch_id)
    if branch is None:
        raise KeyError(f"branch not found: {request.branch_id}")

    result = BranchGetResult(branch=branch)
    return _tool_response(
        result.model_dump(mode="json"),
        f"Branch {branch.branch_id} is {branch.status.value} at stage {branch.current_stage_key.value}.",
    )


def rd_branch_list(request: BranchListRequest, *, state_store: StateStorePort) -> dict[str, Any]:
    run = state_store.load_run_snapshot(request.run_id)
    if run is None:
        raise KeyError(f"run not found: {request.run_id}")

    branches = [
        branch for branch_id in run.branch_ids if (branch := state_store.load_branch_snapshot(branch_id)) is not None
    ]
    if not request.include_completed:
        branches = [branch for branch in branches if branch.status is not BranchStatus.COMPLETED]

    result = BranchListResult(run_id=request.run_id, items=branches)
    branch_summary = ", ".join(branch.branch_id for branch in branches) or "none"
    return _tool_response(
        result.model_dump(mode="json"),
        f"Run {request.run_id} branches: {branch_summary}.",
    )


__all__ = ["rd_branch_get", "rd_branch_list"]
