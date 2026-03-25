"""Explicit Phase 15 branch-isolation path contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BranchIsolationSnapshot(BaseModel):
    """Canonical branch-local and shared roots for a V3 run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    branch_root: str = Field(min_length=1)
    artifact_root: str = Field(min_length=1)
    memory_root: str = Field(min_length=1)
    shared_memory_root: str = Field(min_length=1)
    workspace_root: str = Field(min_length=1)


__all__ = ["BranchIsolationSnapshot"]
