"""Memory-facing V3 tool handlers."""

from __future__ import annotations

from typing import Any

from v3.contracts.tool_io import (
    MemoryCreateRequest,
    MemoryGetRequest,
    MemoryListRequest,
    MemoryPromoteRequest,
)
from v3.orchestration.memory_service import MemoryService


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_memory_create(request: MemoryCreateRequest, *, service: MemoryService) -> dict[str, Any]:
    result = service.create_memory(request)
    return _tool_response(
        result.model_dump(mode="json"),
        f"Created memory {result.memory_id} for owner branch {result.owner_branch_id}.",
    )


def rd_memory_get(request: MemoryGetRequest, *, service: MemoryService) -> dict[str, Any]:
    result = service.get_memory(request)
    status = "local-only"
    if result.shared_namespace is not None:
        status = f"local + {result.shared_namespace.value}"
    text = (
        f"Memory {result.memory_id} status: {status}; owner branch: {result.owner_branch_id}; "
        f"run: {result.run_id}; source namespace: {result.source_namespace.value}."
    )
    if result.promotion_reason:
        text += f" Promotion reason: {result.promotion_reason}."
    return _tool_response(result.model_dump(mode="json"), text)


def rd_memory_list(request: MemoryListRequest, *, service: MemoryService) -> dict[str, Any]:
    result = service.list_memory(request)
    if result.items:
        summary = "; ".join(
            _describe_item(item)
            for item in result.items
        )
    else:
        summary = "none"
    return _tool_response(
        result.model_dump(mode="json"),
        f"Memory results for branch {request.branch_id}: {summary}.",
    )


def rd_memory_promote(request: MemoryPromoteRequest, *, service: MemoryService) -> dict[str, Any]:
    result = service.promote_memory(request)
    if result.can_promote:
        text = (
            f"Promoted memory {result.memory_id} from owner branch {result.owner_branch_id} "
            f"to {result.shared_namespace.value}. Promotion reason: {result.promotion_reason}."
        )
    else:
        text = (
            f"Memory {result.memory_id} from owner branch {result.owner_branch_id} was not promoted. "
            "Supporting evidence or outcome is required."
        )
    return _tool_response(result.model_dump(mode="json"), text)


def _describe_item(item: Any) -> str:
    status = "local"
    if item.source_namespace.value == "shared":
        status = "shared"
    elif item.shared_namespace is not None:
        status = f"local + {item.shared_namespace.value}"

    summary = (
        f"{item.memory_id} [{status}] owner branch {item.owner_branch_id}"
    )
    if item.promotion_reason:
        summary += f" promotion reason: {item.promotion_reason}"
    return summary


__all__ = [
    "rd_memory_create",
    "rd_memory_get",
    "rd_memory_list",
    "rd_memory_promote",
]
