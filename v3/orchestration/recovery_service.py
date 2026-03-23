"""Public V3 recovery assessment over branch-stage state artifacts."""

from __future__ import annotations

from collections.abc import Callable

from v3.contracts.artifact import ArtifactReuseLevel, ArtifactSnapshot
from v3.contracts.recovery import (
    RecoveryAssessment,
    RecoveryDisposition,
    RecoveryReason,
    RecoveryReasonCode,
)
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.ports.recovery import RecoveryInputs
from v3.ports.state_store import StateStorePort


class RecoveryService:
    """Computes public recovery semantics from V3-owned state or translated inputs."""

    def __init__(
        self,
        state_store: StateStorePort,
        *,
        migration_loader: Callable[[str, StageKey], RecoveryInputs | None] | None = None,
    ) -> None:
        self._state_store = state_store
        self._migration_loader = migration_loader

    def assess(self, branch_id: str, stage_key: StageKey, *, allow_backfill: bool = False) -> RecoveryAssessment | None:
        inputs = self._load_inputs(branch_id, stage_key, allow_backfill=allow_backfill)
        if inputs is None:
            return None

        assessment = self.assess_inputs(inputs)
        self._state_store.write_recovery_assessment(assessment)
        return assessment

    def assess_inputs(self, inputs: RecoveryInputs) -> RecoveryAssessment:
        artifacts_by_id = {artifact.artifact_id: artifact for artifact in inputs.artifacts}
        relevant_artifacts = [
            artifacts_by_id[artifact_id]
            for artifact_id in inputs.stage.artifact_ids
            if artifact_id in artifacts_by_id
        ]

        reusable_artifact_ids = [
            artifact.artifact_id
            for artifact in relevant_artifacts
            if artifact.reuse_level in {ArtifactReuseLevel.REUSABLE, ArtifactReuseLevel.REFERENCE}
        ]
        replay_artifact_ids = [
            artifact_id
            for artifact_id in inputs.stage.artifact_ids
            if artifact_id not in reusable_artifact_ids
        ]

        invalid_reasons: list[RecoveryReason] = []
        if len(relevant_artifacts) != len(inputs.stage.artifact_ids):
            invalid_reasons.append(
                RecoveryReason(
                    code=RecoveryReasonCode.ARTIFACTS_MISSING,
                    explanation="Some published stage artifacts are missing from V3 state.",
                )
            )
        if inputs.stage.status is StageStatus.BLOCKED:
            invalid_reasons.append(
                RecoveryReason(
                    code=RecoveryReasonCode.STAGE_BLOCKED,
                    explanation=self._blocked_explanation(inputs.stage),
                )
            )
        elif inputs.stage.status is not StageStatus.COMPLETED:
            invalid_reasons.append(
                RecoveryReason(
                    code=RecoveryReasonCode.STAGE_NOT_FINISHED,
                    explanation=f"{inputs.stage.stage_key.value} has not finished publishing reusable state yet.",
                )
            )
        if any(artifact.reuse_level is ArtifactReuseLevel.REPLAY_REQUIRED for artifact in relevant_artifacts):
            invalid_reasons.append(
                RecoveryReason(
                    code=RecoveryReasonCode.ARTIFACTS_STALE,
                    explanation=f"{inputs.stage.stage_key.value} evidence must be replayed before it can be reused.",
                )
            )
        if any(artifact.reuse_level is ArtifactReuseLevel.NONE for artifact in relevant_artifacts):
            invalid_reasons.append(
                RecoveryReason(
                    code=RecoveryReasonCode.ARTIFACTS_MISSING,
                    explanation=f"{inputs.stage.stage_key.value} did not publish reusable evidence.",
                )
            )

        recovery_assessment = self._disposition_for(inputs.stage, replay_artifact_ids, invalid_reasons)
        recommended_next_step = self._recommended_next_step(inputs.stage, recovery_assessment)

        return RecoveryAssessment(
            run_id=inputs.branch.run_id,
            branch_id=inputs.branch.branch_id,
            stage_key=inputs.stage.stage_key,
            recovery_assessment=recovery_assessment,
            reusable_artifact_ids=reusable_artifact_ids,
            replay_artifact_ids=replay_artifact_ids,
            invalid_reasons=invalid_reasons,
            recommended_next_step=recommended_next_step,
        )

    def _load_inputs(self, branch_id: str, stage_key: StageKey, *, allow_backfill: bool) -> RecoveryInputs | None:
        branch = self._state_store.load_branch_snapshot(branch_id)
        stage = self._state_store.load_stage_snapshot(branch_id, stage_key)
        if branch is not None and stage is not None:
            artifacts = self._state_store.list_artifact_snapshots(
                branch.run_id,
                branch_id=branch_id,
                stage_key=stage_key,
            )
            return RecoveryInputs(branch=branch, stage=stage, artifacts=artifacts)
        if not allow_backfill or self._migration_loader is None:
            return None
        return self._migration_loader(branch_id, stage_key)

    def _disposition_for(
        self,
        stage: StageSnapshot,
        replay_artifact_ids: list[str],
        invalid_reasons: list[RecoveryReason],
    ) -> RecoveryDisposition:
        reason_codes = {reason.code for reason in invalid_reasons}
        if RecoveryReasonCode.ARTIFACTS_MISSING in reason_codes:
            return RecoveryDisposition.REBUILD
        if replay_artifact_ids or RecoveryReasonCode.ARTIFACTS_STALE in reason_codes:
            return RecoveryDisposition.REPLAY
        if stage.status is StageStatus.COMPLETED:
            return RecoveryDisposition.REUSE
        return RecoveryDisposition.REVIEW

    def _recommended_next_step(self, stage: StageSnapshot, recovery_assessment: RecoveryDisposition) -> str:
        next_stage = stage.next_stage_key.value if stage.next_stage_key is not None else "the next stage"
        if recovery_assessment is RecoveryDisposition.REUSE:
            return f"continue with {next_stage}"
        if recovery_assessment is RecoveryDisposition.REPLAY:
            return f"replay {stage.stage_key.value} evidence before advancing to {next_stage}"
        if recovery_assessment is RecoveryDisposition.REBUILD:
            return f"rebuild {stage.stage_key.value} artifacts before advancing to {next_stage}"
        return f"review {stage.stage_key.value} blockers before advancing to {next_stage}"

    def _blocked_explanation(self, stage: StageSnapshot) -> str:
        if stage.blocking_reasons:
            return stage.blocking_reasons[0]
        return f"{stage.stage_key.value} is blocked and needs manual review."


__all__ = ["RecoveryService"]
