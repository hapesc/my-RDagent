"""High-level Phase 16 exploration and convergence tools."""

from __future__ import annotations

from typing import Any

from rd_agent.contracts.tool_io import (
    ConvergeRoundRequest,
    ConvergeRoundResult,
    ExploreRoundRequest,
    ExploreRoundResult,
)
from rd_agent.orchestration.multi_branch_service import MultiBranchService


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_explore_round(request: ExploreRoundRequest, *, service: MultiBranchService) -> dict[str, Any]:
    result = service.run_exploration_round(request)
    structured = ExploreRoundResult.model_validate(result.model_dump(mode="json"))
    return _tool_response(
        structured.model_dump(mode="json"),
        f"Exploration round selected {result.selected_branch_id} and recommends {result.recommended_next_step}.",
    )


def rd_converge_round(request: ConvergeRoundRequest, *, service: MultiBranchService) -> dict[str, Any]:
    result = service.run_convergence_round(request)
    structured = ConvergeRoundResult.model_validate(result.model_dump(mode="json"))
    return _tool_response(
        structured.model_dump(mode="json"),
        f"Convergence round selected {result.selected_branch_id} and recommends {result.recommended_next_step}.",
    )


__all__ = ["rd_converge_round", "rd_explore_round"]
