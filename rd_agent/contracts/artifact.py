"""V3 public evidence contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .stage import StageKey


class ArtifactKind(StrEnum):
    """High-level public evidence categories."""

    NOTE = "note"
    PLAN = "plan"
    CODE = "code"
    EXECUTION_LOG = "execution_log"
    RESULT = "result"
    REVIEW = "review"
    SUMMARY = "summary"


class ArtifactReuseLevel(StrEnum):
    """Whether an artifact can be carried forward without replay."""

    NONE = "none"
    REFERENCE = "reference"
    REPLAY_REQUIRED = "replay_required"
    REUSABLE = "reusable"


class ArtifactLocator(BaseModel):
    """Opaque pointer to the stored artifact payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    uri: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    size_bytes: int | None = Field(default=None, ge=0)


class ArtifactProvenance(BaseModel):
    """Public provenance for where the evidence came from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    created_by: str = Field(min_length=1)
    derived_from_artifact_ids: list[str] = Field(default_factory=list)
    source_branch_ids: list[str] = Field(default_factory=list)
    captured_at: str | None = None


class ArtifactSnapshot(BaseModel):
    """Authoritative public evidence for branch-stage truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    stage_key: StageKey
    kind: ArtifactKind
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    locator: ArtifactLocator
    provenance: ArtifactProvenance
    reuse_level: ArtifactReuseLevel
    tags: list[str] = Field(default_factory=list)


__all__ = [
    "ArtifactKind",
    "ArtifactLocator",
    "ArtifactProvenance",
    "ArtifactReuseLevel",
    "ArtifactSnapshot",
]
