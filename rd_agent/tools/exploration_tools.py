"""Exploration-facing V3 tool handlers."""

from __future__ import annotations

from typing import Any

from rd_agent.contracts.tool_io import (
    BranchBoardGetRequest,
    BranchBoardGetResult,
    BranchFallbackRequest,
    BranchFallbackResult,
    BranchForkRequest,
    BranchMergeRequest,
    BranchMergeResult,
    BranchPruneRequest,
    BranchPruneResult,
    BranchShareApplyRequest,
    BranchShareApplyResult,
    BranchShareAssessRequest,
    BranchShareAssessResult,
    BranchShortlistRequest,
    BranchShortlistResult,
)
from rd_agent.orchestration.branch_board_service import BranchBoardService
from rd_agent.orchestration.branch_lifecycle_service import BranchLifecycleService
from rd_agent.orchestration.branch_merge_service import BranchMergeService
from rd_agent.orchestration.branch_prune_service import BranchPruneService
from rd_agent.orchestration.branch_share_service import BranchShareService
from rd_agent.orchestration.convergence_service import ConvergenceService


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_branch_fork(request: BranchForkRequest, *, service: BranchLifecycleService) -> dict[str, Any]:
    result = service.fork_branch(request)
    return _tool_response(
        result.model_dump(mode="json"),
        f"Forked branch {result.branch.branch_id} for hypothesis {result.branch.label}.",
    )


def rd_branch_board_get(request: BranchBoardGetRequest, *, service: BranchBoardService) -> dict[str, Any]:
    board = service.get_board(request.run_id)
    result = BranchBoardGetResult(board=board)
    return _tool_response(
        result.model_dump(mode="json"),
        (
            f"Run {request.run_id} board has {len(board.active_cards)} active branch(es) "
            f"and {len(board.history_cards)} historical branch(es)."
        ),
    )


def rd_branch_prune(request: BranchPruneRequest, *, service: BranchPruneService) -> dict[str, Any]:
    result = service.prune(request)
    structured = BranchPruneResult.model_validate(result.model_dump(mode="json"))
    return _tool_response(
        structured.model_dump(mode="json"),
        (
            f"Pruned {len(result.pruned_branch_ids)} branch(es) for run {request.run_id}; "
            f"{len(result.active_branch_ids)} branch(es) remain active."
        ),
    )


def rd_branch_share_assess(request: BranchShareAssessRequest, *, service: BranchShareService) -> dict[str, Any]:
    result = service.assess_share(request)
    structured = BranchShareAssessResult.model_validate(result.model_dump(mode="json"))
    return _tool_response(
        structured.model_dump(mode="json"),
        (
            f"Share assessment for {request.source_branch_id}->{request.target_branch_id}:"
            f" {'eligible' if result.eligible else 'denied'}."
        ),
    )


def rd_branch_share_apply(request: BranchShareApplyRequest, *, service: BranchShareService) -> dict[str, Any]:
    result = service.apply_share(request)
    structured = BranchShareApplyResult.model_validate(result.model_dump(mode="json"))
    return _tool_response(
        structured.model_dump(mode="json"),
        (
            f"Shared memory {request.memory_id} from {request.source_branch_id} to {request.target_branch_id} "
            f"at {result.granularity} granularity."
        ),
    )


def rd_branch_shortlist(request: BranchShortlistRequest, *, service: ConvergenceService) -> dict[str, Any]:
    result = service.shortlist(request)
    structured = BranchShortlistResult.model_validate(result.model_dump(mode="json"))
    return _tool_response(
        structured.model_dump(mode="json"),
        f"Built shortlist for run {request.run_id} with {len(result.shortlist)} candidate(s).",
    )


def rd_branch_merge(request: BranchMergeRequest, *, service: BranchMergeService) -> dict[str, Any]:
    result = service.merge(request)
    structured = BranchMergeResult.model_validate(result.model_dump(mode="json"))
    return _tool_response(
        structured.model_dump(mode="json"),
        f"Merge outcome for run {request.run_id}: {result.outcome.summary}",
    )


def rd_branch_fallback(request: BranchFallbackRequest, *, service: BranchMergeService) -> dict[str, Any]:
    result = service.fallback(request)
    structured = BranchFallbackResult.model_validate(result.model_dump(mode="json"))
    return _tool_response(
        structured.model_dump(mode="json"),
        f"Fallback selected {result.selected_branch_id} for run {request.run_id}.",
    )


__all__ = [
    "rd_branch_board_get",
    "rd_branch_fallback",
    "rd_branch_fork",
    "rd_branch_merge",
    "rd_branch_prune",
    "rd_branch_share_apply",
    "rd_branch_share_assess",
    "rd_branch_shortlist",
]
