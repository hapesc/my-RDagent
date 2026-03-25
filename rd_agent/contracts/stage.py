"""V3 branch lifecycle terminology."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StageKey(StrEnum):
    """Stable public lifecycle slices for a V3 branch."""

    FRAMING = "framing"
    BUILD = "build"
    VERIFY = "verify"
    SYNTHESIZE = "synthesize"


class StageStatus(StrEnum):
    """Public progress states for a branch stage."""

    NOT_STARTED = "not_started"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    INVALIDATED = "invalidated"


class StageSnapshot(BaseModel):
    """Current public state for a branch lifecycle stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_key: StageKey
    stage_iteration: int = Field(default=1, ge=1)
    status: StageStatus
    summary: str = Field(min_length=1)
    artifact_ids: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    next_stage_key: StageKey | None = None


__all__ = ["StageKey", "StageSnapshot", "StageStatus"]
