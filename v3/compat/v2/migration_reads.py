"""Read-only legacy metadata access for V3 translation inputs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LegacyBranchStageRecord:
    """Private legacy branch-stage metadata loaded only for translation."""

    run_id: str
    branch_id: str
    stage_name: str
    stage_status: str
    artifact_ids: tuple[str, ...] = ()
    branch_label: str | None = None
    parent_branch_id: str | None = None
    source_summary: str | None = None
    blocking_reasons: tuple[str, ...] = ()
    next_stage_name: str | None = None
    checkpoint_ref: str | None = None


@dataclass(frozen=True)
class LegacyArtifactRecord:
    """Private legacy artifact metadata loaded only for translation."""

    artifact_id: str
    branch_id: str
    stage_name: str
    title: str
    summary: str
    storage_path: str
    media_type: str
    created_by: str
    reuse_hint: str
    derived_from_artifact_ids: tuple[str, ...] = ()
    source_branch_ids: tuple[str, ...] = ()
    captured_at: str | None = None
    checkpoint_ref: str | None = None


@dataclass(frozen=True)
class V2RecoverySnapshotReader:
    """In-memory read-only adapter for historical V2 recovery metadata."""

    stage_records: dict[tuple[str, str], LegacyBranchStageRecord] = field(default_factory=dict)
    artifact_records: dict[tuple[str, str], list[LegacyArtifactRecord]] = field(default_factory=dict)

    def read_branch_stage(self, branch_id: str, stage_name: str) -> LegacyBranchStageRecord | None:
        record = self.stage_records.get((branch_id, stage_name))
        if record is None:
            return None
        return LegacyBranchStageRecord(**record.__dict__)

    def read_artifacts(self, branch_id: str, stage_name: str) -> list[LegacyArtifactRecord]:
        records = self.artifact_records.get((branch_id, stage_name), [])
        return [LegacyArtifactRecord(**record.__dict__) for record in records]


__all__ = [
    "LegacyArtifactRecord",
    "LegacyBranchStageRecord",
    "V2RecoverySnapshotReader",
]
