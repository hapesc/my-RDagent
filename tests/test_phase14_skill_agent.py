from __future__ import annotations

from dataclasses import dataclass

from v3.contracts.artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.run import ExecutionMode, RunStatus, RunStopReason
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import RunStartRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.ports.execution import ExecutionPort, ExecutionStartResult


@dataclass
class _DeterministicExecutionPort(ExecutionPort):
    def start_run(self, request: RunStartRequest) -> ExecutionStartResult:
        artifact = ArtifactSnapshot(
            artifact_id="artifact-framing-001",
            branch_id="branch-001",
            stage_key=StageKey.FRAMING,
            kind=ArtifactKind.PLAN,
            title=request.title,
            summary=request.task_summary,
            locator=ArtifactLocator(
                uri="memory://artifacts/artifact-framing-001.json",
                media_type="application/json",
                size_bytes=128,
            ),
            provenance=ArtifactProvenance(
                created_by="test",
                source_branch_ids=["branch-001"],
                captured_at="2026-03-20T10:00:00Z",
            ),
            reuse_level=ArtifactReuseLevel.REFERENCE,
            tags=["framing"],
        )
        stage = StageSnapshot(
            stage_key=StageKey.FRAMING,
            stage_iteration=1,
            status=StageStatus.IN_PROGRESS,
            summary=f"Framing started for: {request.task_summary}",
            artifact_ids=[artifact.artifact_id],
            next_stage_key=StageKey.BUILD,
        )
        branch = BranchSnapshot(
            branch_id="branch-001",
            run_id="run-001",
            label=request.initial_branch_label,
            status=BranchStatus.ACTIVE,
            current_stage_key=StageKey.FRAMING,
            stages=[stage],
            score=BranchScore(
                exploration_priority=1.0,
                result_quality=0.0,
                rationale="Primary branch remains the active path.",
            ),
            lineage=BranchLineage(source_summary="Created in test state."),
            artifact_ids=[artifact.artifact_id],
        )
        return ExecutionStartResult(branch=branch, stage=stage, artifacts=[artifact])


def test_rd_agent_starts_single_branch_loop(tmp_path) -> None:
    from v3.entry.rd_agent import rd_agent

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(
        state_store=state_store,
        execution_port=_DeterministicExecutionPort(),
    )

    result = rd_agent(
        title="Phase 14 task",
        task_summary="Drive one branch through framing, build, verify, and synthesize.",
        scenario_label="research",
        initial_branch_label="primary",
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=1,
        stage_inputs={
            StageKey.FRAMING: {
                "summary": "Framing completed with a concrete plan.",
                "artifact_ids": ["artifact-framing-001"],
            },
            StageKey.BUILD: {
                "summary": "Build completed with implementation evidence.",
                "artifact_ids": ["artifact-build-001"],
            },
            StageKey.VERIFY: {
                "summary": "Verify completed with passing checks.",
                "artifact_ids": ["artifact-verify-001"],
            },
            StageKey.SYNTHESIZE: {
                "summary": "Synthesize concluded this branch should stop.",
                "artifact_ids": ["artifact-synthesize-001"],
                "recommendation": "stop",
            },
        },
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    run = state_store.load_run_snapshot("run-001")
    branch = state_store.load_branch_snapshot("branch-001")
    build_stage = state_store.load_stage_snapshot("branch-001", StageKey.BUILD)
    verify_stage = state_store.load_stage_snapshot("branch-001", StageKey.VERIFY)
    synthesize_stage = state_store.load_stage_snapshot("branch-001", StageKey.SYNTHESIZE)

    assert result["structuredContent"]["run"]["run_id"] == "run-001"
    assert result["structuredContent"]["branch"]["branch_id"] == "branch-001"
    assert result["structuredContent"]["policy"]["mode"] == "unattended"
    assert result["structuredContent"]["stop_reason"] == "run_completed"
    assert [item["stage_key"] for item in result["structuredContent"]["history"]] == [
        "framing",
        "build",
        "verify",
        "synthesize",
    ]
    assert run is not None
    assert run.status is RunStatus.COMPLETED
    assert run.stop_reason is RunStopReason.RUN_COMPLETED
    assert branch is not None
    assert branch.current_stage_key is StageKey.SYNTHESIZE
    assert build_stage is not None and build_stage.status is StageStatus.COMPLETED
    assert verify_stage is not None and verify_stage.status is StageStatus.COMPLETED
    assert synthesize_stage is not None and synthesize_stage.status is StageStatus.COMPLETED
    assert "advanced to build" in result["content"][0]["text"].lower()
    assert "advanced to verify" in result["content"][0]["text"].lower()
    assert "advanced to synthesize" in result["content"][0]["text"].lower()
    assert "stopped because synthesize recommended stop" in result["content"][0]["text"].lower()
