"""Recovery-facing V3 tool handlers."""

from __future__ import annotations

from typing import Any

from v3.contracts.tool_io import RecoveryAssessRequest, RecoveryAssessResult
from v3.orchestration.recovery_service import RecoveryService


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_recovery_assess(request: RecoveryAssessRequest, *, service: RecoveryService) -> dict[str, Any]:
    assessment = service.assess(request.branch_id, request.stage_key)
    if assessment is None:
        raise KeyError(f"recovery state not found: {request.branch_id}:{request.stage_key.value}")

    result = RecoveryAssessResult(assessment=assessment)
    return _tool_response(
        result.model_dump(mode="json"),
        (
            f"Recovery for branch {assessment.branch_id} at {assessment.stage_key.value}: "
            f"{assessment.disposition.value}. Next: {assessment.recommended_next_step}."
        ),
    )


__all__ = ["rd_recovery_assess"]
