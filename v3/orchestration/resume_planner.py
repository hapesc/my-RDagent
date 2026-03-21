"""Canonical Phase 14 resume decisions derived from V3 state and recovery truth."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from v3.contracts.recovery import RecoveryAssessment, RecoveryDisposition
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus


class ResumeDecision(BaseModel):
    """Single authoritative stage-entry decision for Phase 14 skills."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_key: StageKey
    disposition: RecoveryDisposition
    resume_stage_iteration: int = Field(ge=1)
    should_publish: bool
    reusable_artifact_ids: list[str] = Field(default_factory=list)
    replay_artifact_ids: list[str] = Field(default_factory=list)
    message: str = Field(min_length=1)


def plan_resume_decision(
    *,
    stage: StageSnapshot,
    assessment: RecoveryAssessment | None,
) -> ResumeDecision:
    """Convert V3 stage/recovery truth into a single resume decision."""

    if assessment is None:
        return _decision_without_assessment(stage)

    if assessment.disposition is RecoveryDisposition.REUSE:
        return ResumeDecision(
            stage_key=stage.stage_key,
            disposition=assessment.disposition,
            resume_stage_iteration=stage.stage_iteration,
            should_publish=False,
            reusable_artifact_ids=list(assessment.reusable_artifact_ids),
            replay_artifact_ids=list(assessment.replay_artifact_ids),
            message=(
                f"V3 recovery is reusing {stage.stage_key.value} iteration {stage.stage_iteration}; "
                f"published evidence is reusable, so {assessment.recommended_next_step}."
            ),
        )
    if assessment.disposition is RecoveryDisposition.REPLAY:
        next_iteration = _next_iteration(stage)
        return ResumeDecision(
            stage_key=stage.stage_key,
            disposition=assessment.disposition,
            resume_stage_iteration=next_iteration,
            should_publish=True,
            reusable_artifact_ids=list(assessment.reusable_artifact_ids),
            replay_artifact_ids=list(assessment.replay_artifact_ids),
            message=(
                f"V3 recovery is replaying {stage.stage_key.value} iteration {next_iteration}; "
                f"published evidence is stale, so {assessment.recommended_next_step}."
            ),
        )
    if assessment.disposition is RecoveryDisposition.REBUILD:
        next_iteration = _next_iteration(stage)
        return ResumeDecision(
            stage_key=stage.stage_key,
            disposition=assessment.disposition,
            resume_stage_iteration=next_iteration,
            should_publish=True,
            reusable_artifact_ids=list(assessment.reusable_artifact_ids),
            replay_artifact_ids=list(assessment.replay_artifact_ids),
            message=(
                f"V3 recovery is rebuilding {stage.stage_key.value} iteration {next_iteration}; "
                f"published evidence is incomplete, so {assessment.recommended_next_step}."
            ),
        )
    if stage.status in {StageStatus.NOT_STARTED, StageStatus.READY, StageStatus.IN_PROGRESS}:
        return ResumeDecision(
            stage_key=stage.stage_key,
            disposition=RecoveryDisposition.REBUILD,
            resume_stage_iteration=stage.stage_iteration,
            should_publish=True,
            reusable_artifact_ids=list(assessment.reusable_artifact_ids),
            replay_artifact_ids=list(assessment.replay_artifact_ids),
            message=(
                f"V3 recovery is proceeding with {stage.stage_key.value} iteration {stage.stage_iteration}; "
                f"the stage is ready to run, so {assessment.recommended_next_step}."
            ),
        )
    return ResumeDecision(
        stage_key=stage.stage_key,
        disposition=RecoveryDisposition.REVIEW,
        resume_stage_iteration=stage.stage_iteration,
        should_publish=False,
        reusable_artifact_ids=list(assessment.reusable_artifact_ids),
        replay_artifact_ids=list(assessment.replay_artifact_ids),
        message=_review_message(stage, assessment.recommended_next_step),
    )


def _decision_without_assessment(stage: StageSnapshot) -> ResumeDecision:
    if stage.status is StageStatus.BLOCKED:
        return ResumeDecision(
            stage_key=stage.stage_key,
            disposition=RecoveryDisposition.REVIEW,
            resume_stage_iteration=stage.stage_iteration,
            should_publish=False,
            message=_review_message(stage, f"review {stage.stage_key.value} blockers before advancing"),
        )
    if stage.status is StageStatus.COMPLETED:
        return ResumeDecision(
            stage_key=stage.stage_key,
            disposition=RecoveryDisposition.REVIEW,
            resume_stage_iteration=stage.stage_iteration,
            should_publish=False,
            message=(
                f"V3 recovery needs review before re-entering {stage.stage_key.value}; "
                "completed stage state exists without a persisted recovery assessment."
            ),
        )
    return ResumeDecision(
        stage_key=stage.stage_key,
        disposition=RecoveryDisposition.REBUILD,
        resume_stage_iteration=stage.stage_iteration,
        should_publish=True,
        message=(
            f"V3 recovery is rebuilding {stage.stage_key.value} iteration {stage.stage_iteration}; "
            "no reusable published evidence exists yet."
        ),
    )


def _next_iteration(stage: StageSnapshot) -> int:
    if stage.status in {StageStatus.COMPLETED, StageStatus.BLOCKED, StageStatus.INVALIDATED}:
        return stage.stage_iteration + 1
    return stage.stage_iteration


def _review_message(stage: StageSnapshot, recommended_next_step: str) -> str:
    reason = stage.blocking_reasons[0] if stage.blocking_reasons else "manual review is required."
    return (
        f"V3 recovery is holding {stage.stage_key.value} at iteration {stage.stage_iteration}; "
        f"the stage is blocked and needs manual review before it can proceed. {reason} "
        f"Next step: {recommended_next_step}."
    )


__all__ = ["ResumeDecision", "plan_resume_decision"]
