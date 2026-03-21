"""Translate private V2 recovery metadata into V3-owned contracts."""

from __future__ import annotations

from v3.compat.v2.migration_reads import LegacyArtifactRecord, LegacyBranchStageRecord
from v3.contracts.artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.ports.recovery import RecoveryInputs

_STAGE_KEY_MAP = {
    "propose": StageKey.FRAMING,
    "framing": StageKey.FRAMING,
    "coding": StageKey.BUILD,
    "build": StageKey.BUILD,
    "running": StageKey.VERIFY,
    "feedback": StageKey.VERIFY,
    "verify": StageKey.VERIFY,
    "record": StageKey.SYNTHESIZE,
    "synthesize": StageKey.SYNTHESIZE,
}
_STAGE_STATUS_MAP = {
    "created": StageStatus.NOT_STARTED,
    "ready": StageStatus.READY,
    "running": StageStatus.IN_PROGRESS,
    "in_progress": StageStatus.IN_PROGRESS,
    "blocked": StageStatus.BLOCKED,
    "completed": StageStatus.COMPLETED,
    "invalidated": StageStatus.INVALIDATED,
}
_REUSE_LEVEL_MAP = {
    "none": ArtifactReuseLevel.NONE,
    "reference": ArtifactReuseLevel.REFERENCE,
    "replay_required": ArtifactReuseLevel.REPLAY_REQUIRED,
    "reusable": ArtifactReuseLevel.REUSABLE,
}


def translate_legacy_recovery_inputs(
    stage_record: LegacyBranchStageRecord | None,
    artifact_records: list[LegacyArtifactRecord],
) -> RecoveryInputs | None:
    """Translate legacy recovery metadata into V3-shaped recovery inputs."""

    if stage_record is None:
        return None

    stage = translate_stage_snapshot(stage_record)
    artifacts = [translate_artifact_snapshot(record) for record in artifact_records]
    branch = translate_branch_snapshot(stage_record, stage)
    return RecoveryInputs(branch=branch, stage=stage, artifacts=artifacts)


def translate_branch_snapshot(stage_record: LegacyBranchStageRecord, stage: StageSnapshot) -> BranchSnapshot:
    """Translate one legacy branch-stage record into an opaque public branch snapshot."""

    return BranchSnapshot(
        branch_id=stage_record.branch_id,
        run_id=stage_record.run_id,
        label=stage_record.branch_label,
        status=_branch_status_for(stage.status),
        current_stage_key=stage.stage_key,
        stages=[stage],
        score=BranchScore(
            exploration_priority=0.0,
            result_quality=0.0,
            rationale="Translated historical branch snapshot.",
        ),
        lineage=BranchLineage(
            parent_branch_id=stage_record.parent_branch_id,
            source_summary=stage_record.source_summary,
        ),
        artifact_ids=list(stage_record.artifact_ids),
    )


def translate_stage_snapshot(stage_record: LegacyBranchStageRecord) -> StageSnapshot:
    """Translate legacy stage naming/status into V3 lifecycle semantics."""

    stage_key = _translate_stage_key(stage_record.stage_name)
    next_stage_key = _translate_stage_key(stage_record.next_stage_name) if stage_record.next_stage_name else None
    return StageSnapshot(
        stage_key=stage_key,
        status=_translate_stage_status(stage_record.stage_status),
        summary=f"Translated historical {stage_key.value} stage.",
        artifact_ids=list(stage_record.artifact_ids),
        blocking_reasons=list(stage_record.blocking_reasons),
        next_stage_key=next_stage_key,
    )


def translate_artifact_snapshot(record: LegacyArtifactRecord) -> ArtifactSnapshot:
    """Translate one legacy artifact descriptor into V3 public evidence."""

    stage_key = _translate_stage_key(record.stage_name)
    source_branch_ids = list(record.source_branch_ids) if record.source_branch_ids else [record.branch_id]
    return ArtifactSnapshot(
        artifact_id=record.artifact_id,
        branch_id=record.branch_id,
        stage_key=stage_key,
        kind=ArtifactKind.RESULT,
        title=record.title,
        summary=record.summary,
        locator=ArtifactLocator(
            uri=f"legacy://{record.storage_path}",
            media_type=record.media_type,
        ),
        provenance=ArtifactProvenance(
            created_by=record.created_by,
            derived_from_artifact_ids=list(record.derived_from_artifact_ids),
            source_branch_ids=source_branch_ids,
            captured_at=record.captured_at,
        ),
        reuse_level=_translate_reuse_level(record.reuse_hint),
        tags=[stage_key.value, "translated-v2"],
    )


def _translate_stage_key(name: str) -> StageKey:
    try:
        return _STAGE_KEY_MAP[name.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported legacy stage name: {name}") from exc


def _translate_stage_status(status: str) -> StageStatus:
    try:
        return _STAGE_STATUS_MAP[status.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported legacy stage status: {status}") from exc


def _translate_reuse_level(reuse_hint: str) -> ArtifactReuseLevel:
    try:
        return _REUSE_LEVEL_MAP[reuse_hint.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported legacy reuse hint: {reuse_hint}") from exc


def _branch_status_for(stage_status: StageStatus) -> BranchStatus:
    if stage_status is StageStatus.BLOCKED:
        return BranchStatus.BLOCKED
    if stage_status is StageStatus.COMPLETED:
        return BranchStatus.ACTIVE
    if stage_status is StageStatus.INVALIDATED:
        return BranchStatus.SUPERSEDED
    return BranchStatus.PAUSED


__all__ = [
    "translate_artifact_snapshot",
    "translate_branch_snapshot",
    "translate_legacy_recovery_inputs",
    "translate_stage_snapshot",
]
