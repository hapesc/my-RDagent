"""Shared Phase 24 operator-guidance contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OperatorGuidance(BaseModel):
    """Canonical operator-facing next-step guidance shared across surfaces."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    current_state: str = Field(min_length=1)
    routing_reason: str = Field(min_length=1)
    exact_next_action: str = Field(min_length=1)
    recommended_next_skill: str = Field(min_length=1)
    current_action_status: str | None = None
    current_blocker_category: str | None = None
    current_blocker_reason: str | None = None
    repair_action: str | None = None
    next_step_detail: str | None = None


__all__ = ["OperatorGuidance"]
