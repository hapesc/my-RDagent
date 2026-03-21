"""Run-facing V3 tool handlers."""

from __future__ import annotations

from typing import Any

from v3.contracts.tool_io import RunGetRequest, RunGetResult, RunStartRequest
from v3.orchestration.run_board_service import RunBoardService


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_run_start(request: RunStartRequest, *, service: RunBoardService) -> dict[str, Any]:
    publication = service.start_run(request)
    return _tool_response(
        {
            "run": publication.run.model_dump(mode="json"),
            "branch": publication.branch.model_dump(mode="json"),
            "stage": publication.stage.model_dump(mode="json"),
            "artifacts": [artifact.model_dump(mode="json") for artifact in publication.artifacts],
        },
        (
            f"Started run {publication.run.run_id} with branch {publication.branch.branch_id} "
            f"at stage {publication.stage.stage_key.value}."
        ),
    )


def rd_run_get(request: RunGetRequest, *, service: RunBoardService) -> dict[str, Any]:
    run = service.get_run(request.run_id)
    if run is None:
        raise KeyError(f"run not found: {request.run_id}")

    result = RunGetResult(run=run)
    return _tool_response(
        result.model_dump(mode="json"),
        f"Run {run.run_id} is {run.status.value} with {len(run.branch_ids)} branch(es).",
    )


__all__ = ["rd_run_get", "rd_run_start"]
