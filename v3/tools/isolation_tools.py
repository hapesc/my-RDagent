"""Branch-isolation V3 tool handlers."""

from __future__ import annotations

from typing import Any

from v3.contracts.tool_io import BranchPathsGetRequest, BranchPathsGetResult
from v3.orchestration.branch_isolation_service import BranchIsolationService


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_branch_paths_get(request: BranchPathsGetRequest, *, service: BranchIsolationService) -> dict[str, Any]:
    result = BranchPathsGetResult(paths=service.snapshot(run_id=request.run_id, branch_id=request.branch_id))
    paths = result.paths
    text = (
        f"Branch {request.branch_id} paths: "
        f"artifact_root={paths.artifact_root}, "
        f"workspace_root={paths.workspace_root}, "
        f"memory_root={paths.memory_root}, "
        f"shared_memory_root={paths.shared_memory_root}."
    )
    return _tool_response(result.model_dump(mode='json'), text)


__all__ = ["rd_branch_paths_get"]
