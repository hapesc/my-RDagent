"""V3 recovery assessment contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .stage import StageKey


class RecoveryReasonCode(StrEnum):
    """Machine-readable reasons why a stage can or cannot be reused."""

    ARTIFACTS_MISSING = "artifacts_missing"
    ARTIFACTS_STALE = "artifacts_stale"
    INPUTS_CHANGED = "inputs_changed"
    STAGE_NOT_FINISHED = "stage_not_finished"
    STAGE_BLOCKED = "stage_blocked"
    DEPENDENCY_MISMATCH = "dependency_mismatch"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class RecoveryDisposition(StrEnum):
    """Recommended public action for the assessed stage."""

    REUSE = "reuse"
    REPLAY = "replay"
    REBUILD = "rebuild"
    REVIEW = "review"


class RecoveryReason(BaseModel):
    """Structured explanation for a recovery judgment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: RecoveryReasonCode
    explanation: str = Field(min_length=1)


class RecoveryAssessment(BaseModel):
    """State-first branch recovery judgment without checkpoint leakage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    stage_key: StageKey
    recovery_assessment: RecoveryDisposition
    reusable_artifact_ids: list[str] = Field(default_factory=list)
    replay_artifact_ids: list[str] = Field(default_factory=list)
    invalid_reasons: list[RecoveryReason] = Field(default_factory=list)
    recommended_next_step: str = Field(min_length=1)


__all__ = [
    "RecoveryAssessment",
    "RecoveryDisposition",
    "RecoveryReason",
    "RecoveryReasonCode",
]
