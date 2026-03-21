"""Selection-facing V3 tool handlers."""

from __future__ import annotations

from typing import Any

from v3.contracts.tool_io import (
    BranchSelectNextRecommendation,
    BranchSelectNextRequest,
    BranchSelectNextResult,
)
from v3.orchestration.selection_service import SelectionService
from v3.ports.state_store import StateStorePort


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_branch_select_next(
    request: BranchSelectNextRequest,
    *,
    state_store: StateStorePort,
) -> dict[str, Any]:
    recommendation = SelectionService(state_store=state_store).select_next_branch(
        run_id=request.run_id,
        include_completed=request.include_completed,
    )
    result = BranchSelectNextResult(
        recommendation=BranchSelectNextRecommendation.model_validate(recommendation.__dict__)
    )
    return _tool_response(
        result.model_dump(mode="json"),
        (
            f"Recommended branch {recommendation.branch_id} for run {request.run_id}. "
            f"Next: {recommendation.recommended_next_step}."
        ),
    )


__all__ = [
    "BranchSelectNextRecommendation",
    "BranchSelectNextRequest",
    "BranchSelectNextResult",
    "rd_branch_select_next",
]
