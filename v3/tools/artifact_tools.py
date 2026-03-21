"""Artifact-facing V3 tool handlers."""

from __future__ import annotations

from typing import Any

from v3.contracts.tool_io import ArtifactListRequest, ArtifactListResult
from v3.ports.state_store import StateStorePort


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_artifact_list(request: ArtifactListRequest, *, state_store: StateStorePort) -> dict[str, Any]:
    artifacts = state_store.list_artifact_snapshots(
        request.run_id,
        branch_id=request.branch_id,
        stage_key=request.stage_key,
    )
    if request.kind is not None:
        artifacts = [artifact for artifact in artifacts if artifact.kind is request.kind]

    result = ArtifactListResult(
        run_id=request.run_id,
        branch_id=request.branch_id,
        items=artifacts,
    )
    artifact_summary = ", ".join(artifact.artifact_id for artifact in artifacts) or "none"
    return _tool_response(
        result.model_dump(mode="json"),
        f"Artifacts for run {request.run_id}: {artifact_summary}.",
    )


__all__ = ["rd_artifact_list"]
