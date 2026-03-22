"""Canonical Phase 23 preflight truth contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .stage import StageKey


class PreflightReadiness(StrEnum):
    """Top-level executability result for a stage recommendation or entry."""

    EXECUTABLE = "executable"
    BLOCKED = "blocked"


class PreflightBlockerCategory(StrEnum):
    """Locked blocker categories for Phase 23 operator truth."""

    RUNTIME = "runtime"
    DEPENDENCY = "dependency"
    ARTIFACT = "artifact"
    STATE = "state"
    RECOVERY = "recovery"


class PreflightBlocker(BaseModel):
    """Single blocker with operator-facing reason and repair action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: PreflightBlockerCategory
    reason: str = Field(min_length=1)
    repair_action: str = Field(min_length=1)


class PreflightBlockersByCategory(BaseModel):
    """Grouped blocker inventory for all locked Phase 23 categories."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime: list[PreflightBlocker] = Field(default_factory=list)
    dependency: list[PreflightBlocker] = Field(default_factory=list)
    artifact: list[PreflightBlocker] = Field(default_factory=list)
    state: list[PreflightBlocker] = Field(default_factory=list)
    recovery: list[PreflightBlocker] = Field(default_factory=list)


class PreflightResult(BaseModel):
    """Canonical preflight assessment shared by routing and stage entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    stage_key: StageKey
    recommended_next_skill: str = Field(min_length=1)
    readiness: PreflightReadiness
    primary_blocker_category: PreflightBlockerCategory | None = None
    primary_blocker_reason: str | None = None
    repair_action: str = Field(min_length=1)
    blockers_by_category: PreflightBlockersByCategory = Field(default_factory=PreflightBlockersByCategory)


__all__ = [
    "PreflightBlocker",
    "PreflightBlockerCategory",
    "PreflightBlockersByCategory",
    "PreflightReadiness",
    "PreflightResult",
]
