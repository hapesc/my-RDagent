"""Stage publication tools for V3 skill-facing writes."""

from __future__ import annotations

from typing import Any

from v3.contracts.stage import StageSnapshot, StageStatus
from v3.contracts.tool_io import (
    StageBlockRequest,
    StageCompleteRequest,
    StageStartRequest,
    StageTransitionRequest,
    StageWriteResult,
)
from v3.orchestration.stage_transition_service import StageTransitionService


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def _publish(
    stage_snapshot: StageSnapshot,
    *,
    branch_id: str,
    publisher: Any,
    action: str,
) -> dict[str, Any]:
    branch = publisher(branch_id, stage_snapshot)
    result = StageWriteResult(branch=branch, stage=stage_snapshot)
    return _tool_response(
        result.model_dump(mode="json"),
        (
            f"{action} {stage_snapshot.stage_key.value} iteration {stage_snapshot.stage_iteration} "
            f"as {stage_snapshot.status.value} for branch {branch_id}."
        ),
    )


def rd_stage_start(request: StageStartRequest, *, service: StageTransitionService) -> dict[str, Any]:
    stage_snapshot = StageSnapshot(
        stage_key=request.stage_key,
        stage_iteration=request.stage_iteration,
        status=StageStatus.IN_PROGRESS,
        summary=request.summary,
        artifact_ids=request.artifact_ids,
        next_stage_key=request.next_stage_key,
    )
    return _publish(
        stage_snapshot,
        branch_id=request.branch_id,
        publisher=service.publish_stage_start,
        action="Started",
    )


def rd_stage_complete(request: StageCompleteRequest, *, service: StageTransitionService) -> dict[str, Any]:
    stage_snapshot = StageSnapshot(
        stage_key=request.stage_key,
        stage_iteration=request.stage_iteration,
        status=StageStatus.COMPLETED,
        summary=request.summary,
        artifact_ids=request.artifact_ids,
        next_stage_key=request.next_stage_key,
    )
    return _publish(
        stage_snapshot,
        branch_id=request.branch_id,
        publisher=service.publish_stage_complete,
        action="Completed",
    )


def rd_stage_block(request: StageBlockRequest, *, service: StageTransitionService) -> dict[str, Any]:
    stage_snapshot = StageSnapshot(
        stage_key=request.stage_key,
        stage_iteration=request.stage_iteration,
        status=StageStatus.BLOCKED,
        summary=request.summary,
        artifact_ids=request.artifact_ids,
        blocking_reasons=request.blocking_reasons,
        next_stage_key=request.next_stage_key,
    )
    return _publish(
        stage_snapshot,
        branch_id=request.branch_id,
        publisher=service.publish_stage_block,
        action="Blocked",
    )


def rd_stage_replay(request: StageStartRequest, *, service: StageTransitionService) -> dict[str, Any]:
    stage_snapshot = StageSnapshot(
        stage_key=request.stage_key,
        stage_iteration=request.stage_iteration,
        status=StageStatus.IN_PROGRESS,
        summary=request.summary,
        artifact_ids=request.artifact_ids,
        next_stage_key=request.next_stage_key,
    )
    return _publish(
        stage_snapshot,
        branch_id=request.branch_id,
        publisher=service.publish_stage_replay,
        action="Published replay for",
    )


def rd_stage_transition(request: StageTransitionRequest, *, service: StageTransitionService) -> dict[str, Any]:
    stage_snapshot = StageSnapshot(
        stage_key=request.stage_key,
        stage_iteration=request.stage_iteration,
        status=request.status,
        summary=request.summary,
        artifact_ids=request.artifact_ids,
        blocking_reasons=request.blocking_reasons,
        next_stage_key=request.next_stage_key,
    )
    return _publish(
        stage_snapshot,
        branch_id=request.branch_id,
        publisher=service.publish_stage_transition,
        action="Published",
    )


__all__ = [
    "rd_stage_block",
    "rd_stage_complete",
    "rd_stage_replay",
    "rd_stage_start",
    "rd_stage_transition",
]
