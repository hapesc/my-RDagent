"""Concrete V3 execution handoff for publishing initial run truth."""

from __future__ import annotations

import uuid

from v3.contracts.artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import RunStartRequest
from v3.ports.execution import ExecutionPort, ExecutionStartResult


class V3ExecutionAdapter(ExecutionPort):
    """Creates the initial branch, stage, and evidence for a new V3 run."""

    def start_run(self, request: RunStartRequest) -> ExecutionStartResult:
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        branch_id = f"branch-{uuid.uuid4().hex[:8]}"
        artifact_id = f"artifact-{uuid.uuid4().hex[:8]}"
        stage = StageSnapshot(
            stage_key=StageKey.FRAMING,
            status=StageStatus.IN_PROGRESS,
            summary=f"Framing started for: {request.task_summary}",
            artifact_ids=[artifact_id],
            next_stage_key=StageKey.BUILD,
        )
        artifact = ArtifactSnapshot(
            artifact_id=artifact_id,
            branch_id=branch_id,
            stage_key=StageKey.FRAMING,
            kind=ArtifactKind.PLAN,
            title=request.title,
            summary=request.task_summary,
            locator=ArtifactLocator(
                uri=f"v3://runs/{run_id}/branches/{branch_id}/artifacts/{artifact_id}",
                media_type="application/json",
            ),
            provenance=ArtifactProvenance(
                created_by="v3.execution_adapter",
                source_branch_ids=[branch_id],
            ),
            reuse_level=ArtifactReuseLevel.REFERENCE,
            tags=["run-start", "framing"],
        )
        branch = BranchSnapshot(
            branch_id=branch_id,
            run_id=run_id,
            label=request.initial_branch_label,
            status=BranchStatus.ACTIVE,
            current_stage_key=stage.stage_key,
            stages=[stage],
            score=BranchScore(
                exploration_priority=1.0,
                result_quality=0.0,
                rationale="Newly started branch should be explored before secondary options exist.",
            ),
            lineage=BranchLineage(source_summary="Created from the V3 run start request."),
            artifact_ids=[artifact_id],
        )
        return ExecutionStartResult(branch=branch, stage=stage, artifacts=[artifact])


__all__ = ["V3ExecutionAdapter"]
