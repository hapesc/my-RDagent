"""V3 public memory contracts."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from .stage import StageKey


class MemoryKind(StrEnum):
    """Stable public record shapes for V3 memory."""

    ATOMIC = "atomic"
    STAGE_SUMMARY = "stage_summary"


class MemoryNamespace(StrEnum):
    """Visible storage scopes for Phase 15 memory."""

    BRANCH = "branch"
    SHARED = "shared"


_MEMORY_ID_UNSAFE_PATTERN = re.compile(r"[*?\[\]/\\]")


def validate_memory_id(value: str) -> str:
    candidate = value.strip()
    if candidate in {".", ".."}:
        raise ValueError("memory_id must not be a relative traversal segment")
    if _MEMORY_ID_UNSAFE_PATTERN.search(candidate):
        raise ValueError("memory_id must not contain path separators or glob metacharacters")
    return candidate


MemoryId = Annotated[str, Field(min_length=1), AfterValidator(validate_memory_id)]


class MemoryRecordSnapshot(BaseModel):
    """Authoritative branch-owned memory record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: MemoryId
    run_id: str = Field(min_length=1)
    owner_branch_id: str = Field(min_length=1)
    stage_key: StageKey
    kind: MemoryKind
    hypothesis: str = Field(min_length=1)
    score: float = Field(ge=0.0)
    reason: str = Field(min_length=1)
    evidence: list[str] | None = None
    outcome: str | None = None
    tags: list[str] = Field(default_factory=list)


class MemoryPromotionSnapshot(BaseModel):
    """Shared overlay for a promoted branch-owned memory record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: MemoryId
    run_id: str = Field(min_length=1)
    owner_branch_id: str = Field(min_length=1)
    promotion_reason: str = Field(min_length=1)
    promoted_by: str = Field(min_length=1)
    promoted_at: str = Field(min_length=1)
    shared_namespace: MemoryNamespace


__all__ = [
    "MemoryKind",
    "MemoryId",
    "MemoryNamespace",
    "MemoryPromotionSnapshot",
    "MemoryRecordSnapshot",
    "validate_memory_id",
]
