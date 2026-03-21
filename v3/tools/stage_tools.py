"""Stage-facing V3 tool handlers."""

from __future__ import annotations

from typing import Any

from v3.contracts.tool_io import StageGetRequest, StageGetResult
from v3.ports.state_store import StateStorePort


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_stage_get(request: StageGetRequest, *, state_store: StateStorePort) -> dict[str, Any]:
    stage = state_store.load_stage_snapshot(request.branch_id, request.stage_key)
    if stage is None:
        raise KeyError(f"stage not found: {request.branch_id}:{request.stage_key.value}")

    artifacts = state_store.list_artifact_snapshots(
        run_id=state_store.load_branch_snapshot(request.branch_id).run_id,  # type: ignore[union-attr]
        branch_id=request.branch_id,
        stage_key=request.stage_key,
    )
    result = StageGetResult(
        branch_id=request.branch_id,
        stage_key=request.stage_key,
        stage=stage,
        items=artifacts,
    )
    return _tool_response(
        result.model_dump(mode="json"),
        (
            f"Branch {request.branch_id} stage {request.stage_key.value} is "
            f"{stage.status.value} with {len(artifacts)} artifact(s)."
        ),
    )


__all__ = ["rd_stage_get"]
