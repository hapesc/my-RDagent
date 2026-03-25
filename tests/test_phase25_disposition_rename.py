from __future__ import annotations

import pytest
from pydantic import ValidationError

from rd_agent.contracts.recovery import RecoveryAssessment, RecoveryDisposition
from rd_agent.contracts.stage import StageKey, StageSnapshot, StageStatus
from rd_agent.orchestration.resume_planner import ResumeDecision, plan_resume_decision


def _assessment(
    *,
    recovery_assessment: RecoveryDisposition = RecoveryDisposition.REUSE,
) -> RecoveryAssessment:
    return RecoveryAssessment(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=StageKey.BUILD,
        recovery_assessment=recovery_assessment,
        reusable_artifact_ids=["build-artifact-001"],
        replay_artifact_ids=[],
        invalid_reasons=[],
        recommended_next_step="continue with verify",
    )


def test_recovery_assessment_accepts_recovery_assessment_field() -> None:
    assessment = _assessment()

    assert assessment.recovery_assessment is RecoveryDisposition.REUSE
    payload = assessment.model_dump(mode="json")
    assert payload["recovery_assessment"] == RecoveryDisposition.REUSE.value
    assert "disposition" not in payload


def test_recovery_assessment_rejects_disposition_field() -> None:
    with pytest.raises(ValidationError):
        RecoveryAssessment(
            run_id="run-001",
            branch_id="branch-001",
            stage_key=StageKey.BUILD,
            disposition=RecoveryDisposition.REUSE,
            reusable_artifact_ids=["build-artifact-001"],
            replay_artifact_ids=[],
            invalid_reasons=[],
            recommended_next_step="continue with verify",
        )


def test_resume_decision_accepts_recovery_assessment_field() -> None:
    decision = ResumeDecision(
        stage_key=StageKey.BUILD,
        recovery_assessment=RecoveryDisposition.REUSE,
        resume_stage_iteration=1,
        should_publish=False,
        reusable_artifact_ids=["build-artifact-001"],
        replay_artifact_ids=[],
        message="Current state: build stage (`build`) already has reusable evidence.",
    )

    assert decision.recovery_assessment is RecoveryDisposition.REUSE
    payload = decision.model_dump(mode="json")
    assert payload["recovery_assessment"] == RecoveryDisposition.REUSE.value
    assert "disposition" not in payload


def test_resume_decision_rejects_disposition_field() -> None:
    with pytest.raises(ValidationError):
        ResumeDecision(
            stage_key=StageKey.BUILD,
            disposition=RecoveryDisposition.REUSE,
            resume_stage_iteration=1,
            should_publish=False,
            reusable_artifact_ids=["build-artifact-001"],
            replay_artifact_ids=[],
            message="Current state: build stage (`build`) already has reusable evidence.",
        )


def test_plan_resume_decision_exposes_recovery_assessment_attribute() -> None:
    stage = StageSnapshot(
        stage_key=StageKey.BUILD,
        stage_iteration=1,
        status=StageStatus.COMPLETED,
        summary="Build summary",
        artifact_ids=["build-artifact-001"],
        next_stage_key=StageKey.VERIFY,
    )

    decision = plan_resume_decision(
        stage=stage,
        assessment=_assessment(recovery_assessment=RecoveryDisposition.REPLAY),
    )

    assert decision.recovery_assessment is RecoveryDisposition.REPLAY
    payload = decision.model_dump(mode="json")
    assert payload["recovery_assessment"] == RecoveryDisposition.REPLAY.value
    assert "disposition" not in payload
