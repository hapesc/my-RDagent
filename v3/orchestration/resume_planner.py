"""Canonical Phase 14 resume decisions derived from V3 state and recovery truth."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from v3.contracts.recovery import RecoveryAssessment, RecoveryDisposition
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.orchestration.operator_guidance import render_operator_guidance_text


class ResumeDecision(BaseModel):
    """Single authoritative stage-entry decision for Phase 14 skills."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_key: StageKey
    recovery_assessment: RecoveryDisposition
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

    if assessment.recovery_assessment is RecoveryDisposition.REUSE:
        return ResumeDecision(
            stage_key=stage.stage_key,
            recovery_assessment=assessment.recovery_assessment,
            resume_stage_iteration=stage.stage_iteration,
            should_publish=False,
            reusable_artifact_ids=list(assessment.reusable_artifact_ids),
            replay_artifact_ids=list(assessment.replay_artifact_ids),
            message=_format_resume_message(
                current_state=(
                    f"Current state: {stage.stage_key.value} stage (`{stage.stage_key.value}`) "
                    f"iteration {stage.stage_iteration} already has reusable evidence."
                ),
                reason="Reason: published evidence is reusable, so a new publish is unnecessary.",
                next_action=f"Next action: {assessment.recommended_next_step}.",
            ),
        )
    if assessment.recovery_assessment is RecoveryDisposition.REPLAY:
        next_iteration = _next_iteration(stage)
        return ResumeDecision(
            stage_key=stage.stage_key,
            recovery_assessment=assessment.recovery_assessment,
            resume_stage_iteration=next_iteration,
            should_publish=True,
            reusable_artifact_ids=list(assessment.reusable_artifact_ids),
            replay_artifact_ids=list(assessment.replay_artifact_ids),
            message=_format_resume_message(
                current_state=(
                    f"Current state: {stage.stage_key.value} stage (`{stage.stage_key.value}`) "
                    f"needs replay at iteration {next_iteration}."
                ),
                reason="Reason: published evidence is stale and must be replayed before the next handoff is trustworthy.",
                next_action=f"Next action: {assessment.recommended_next_step}.",
            ),
        )
    if assessment.recovery_assessment is RecoveryDisposition.REBUILD:
        next_iteration = _next_iteration(stage)
        return ResumeDecision(
            stage_key=stage.stage_key,
            recovery_assessment=assessment.recovery_assessment,
            resume_stage_iteration=next_iteration,
            should_publish=True,
            reusable_artifact_ids=list(assessment.reusable_artifact_ids),
            replay_artifact_ids=list(assessment.replay_artifact_ids),
            message=_format_resume_message(
                current_state=(
                    f"Current state: {stage.stage_key.value} stage (`{stage.stage_key.value}`) "
                    f"must rebuild at iteration {next_iteration}."
                ),
                reason="Reason: published evidence is incomplete, so the stage cannot safely hand off yet.",
                next_action=f"Next action: {assessment.recommended_next_step}.",
            ),
        )
    if stage.status in {StageStatus.NOT_STARTED, StageStatus.READY, StageStatus.IN_PROGRESS}:
        return ResumeDecision(
            stage_key=stage.stage_key,
            recovery_assessment=RecoveryDisposition.REBUILD,
            resume_stage_iteration=stage.stage_iteration,
            should_publish=True,
            reusable_artifact_ids=list(assessment.reusable_artifact_ids),
            replay_artifact_ids=list(assessment.replay_artifact_ids),
            message=_format_resume_message(
                current_state=(
                    f"Current state: {stage.stage_key.value} stage (`{stage.stage_key.value}`) "
                    f"iteration {stage.stage_iteration} is prepared but not yet executed."
                ),
                reason=(
                    "Reason: the stage still requires canonical preflight truth before execution can be treated as safe."
                ),
                next_action=f"Next action: {assessment.recommended_next_step}.",
            ),
        )
    return ResumeDecision(
        stage_key=stage.stage_key,
        recovery_assessment=RecoveryDisposition.REVIEW,
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
            recovery_assessment=RecoveryDisposition.REVIEW,
            resume_stage_iteration=stage.stage_iteration,
            should_publish=False,
            message=_review_message(stage, f"review {stage.stage_key.value} blockers before advancing"),
        )
    if stage.status is StageStatus.COMPLETED:
        return ResumeDecision(
            stage_key=stage.stage_key,
            recovery_assessment=RecoveryDisposition.REVIEW,
            resume_stage_iteration=stage.stage_iteration,
            should_publish=False,
            message=_format_resume_message(
                current_state=(
                    f"Current state: {stage.stage_key.value} stage (`{stage.stage_key.value}`) "
                    f"iteration {stage.stage_iteration} is completed."
                ),
                reason="Reason: completed stage state exists without a persisted recovery assessment.",
                next_action=f"Next action: review {stage.stage_key.value} before re-entering it.",
            ),
        )
    return ResumeDecision(
        stage_key=stage.stage_key,
        recovery_assessment=RecoveryDisposition.REBUILD,
        resume_stage_iteration=stage.stage_iteration,
        should_publish=True,
        message=_format_resume_message(
            current_state=(
                f"Current state: {stage.stage_key.value} stage (`{stage.stage_key.value}`) "
                f"iteration {stage.stage_iteration} has no reusable evidence yet."
            ),
            reason="Reason: no reusable published evidence exists yet.",
            next_action=f"Next action: rebuild {stage.stage_key.value} iteration {stage.stage_iteration}.",
        ),
    )


def _next_iteration(stage: StageSnapshot) -> int:
    if stage.status in {StageStatus.COMPLETED, StageStatus.BLOCKED, StageStatus.INVALIDATED}:
        return stage.stage_iteration + 1
    return stage.stage_iteration


def _review_message(stage: StageSnapshot, recommended_next_step: str) -> str:
    reason = stage.blocking_reasons[0] if stage.blocking_reasons else "manual review is required."
    return _format_resume_message(
        current_state=(
            f"Current state: {stage.stage_key.value} stage (`{stage.stage_key.value}`) "
            f"iteration {stage.stage_iteration} is blocked."
        ),
        reason=f"Reason: {reason}",
        next_action=f"Next action: {recommended_next_step}.",
    )


def _format_resume_message(*, current_state: str, reason: str, next_action: str) -> str:
    return render_operator_guidance_text(
        {
            "current_state": current_state,
            "routing_reason": reason,
            "exact_next_action": next_action,
        }
    )


__all__ = ["ResumeDecision", "plan_resume_decision"]
