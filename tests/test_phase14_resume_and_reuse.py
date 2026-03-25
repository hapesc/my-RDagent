from __future__ import annotations

from pathlib import Path

from rd_agent.contracts.artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from rd_agent.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from rd_agent.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from rd_agent.contracts.stage import StageKey, StageSnapshot, StageStatus
from rd_agent.orchestration.artifact_state_store import ArtifactStateStore
from rd_agent.orchestration.recovery_service import RecoveryService
from rd_agent.orchestration.resume_planner import plan_resume_decision
from rd_agent.orchestration.run_board_service import RunBoardService
from rd_agent.orchestration.stage_transition_service import StageTransitionService


def _artifact(
    artifact_id: str,
    branch_id: str,
    stage_key: StageKey,
    *,
    reuse_level: ArtifactReuseLevel,
) -> ArtifactSnapshot:
    return ArtifactSnapshot(
        artifact_id=artifact_id,
        branch_id=branch_id,
        stage_key=stage_key,
        kind=ArtifactKind.PLAN,
        title=f"{artifact_id} title",
        summary=f"{artifact_id} summary",
        locator=ArtifactLocator(
            uri=f"memory://artifacts/{artifact_id}.json",
            media_type="application/json",
            size_bytes=128,
        ),
        provenance=ArtifactProvenance(
            created_by="test",
            source_branch_ids=[branch_id],
            captured_at="2026-03-20T10:00:00Z",
        ),
        reuse_level=reuse_level,
        tags=[stage_key.value],
    )


def _seed_stage(
    tmp_path: Path,
    *,
    stage_key: StageKey,
    stage_status: StageStatus,
    artifact_reuse_level: ArtifactReuseLevel,
    next_stage_key: StageKey | None,
) -> tuple[ArtifactStateStore, StageSnapshot]:
    state_store = ArtifactStateStore(tmp_path / "state")
    stage = StageSnapshot(
        stage_key=stage_key,
        stage_iteration=1,
        status=stage_status,
        summary=f"{stage_key.value} summary",
        artifact_ids=[f"{stage_key.value}-artifact-001"],
        blocking_reasons=["Manual review is required."] if stage_status is StageStatus.BLOCKED else [],
        next_stage_key=next_stage_key,
    )
    branch = BranchSnapshot(
        branch_id="branch-001",
        run_id="run-001",
        label="Primary branch",
        status=BranchStatus.ACTIVE,
        current_stage_key=stage_key,
        stages=[stage],
        score=BranchScore(
            exploration_priority=0.8,
            result_quality=0.5,
            rationale="Primary branch remains the active path.",
        ),
        lineage=BranchLineage(source_summary="Created in test state."),
        artifact_ids=list(stage.artifact_ids),
    )
    run = RunBoardSnapshot(
        run_id="run-001",
        title="Phase 14",
        scenario_label="research",
        status=RunStatus.ACTIVE,
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=3,
        primary_branch_id=branch.branch_id,
        branch_ids=[branch.branch_id],
        highlighted_artifact_ids=list(stage.artifact_ids),
        summary="Active run board.",
    )
    state_store.write_run_snapshot(run)
    state_store.write_branch_snapshot(branch)
    state_store.write_stage_snapshot(branch.branch_id, stage)
    state_store.write_artifact_snapshot(
        _artifact(
            stage.artifact_ids[0],
            branch.branch_id,
            stage_key,
            reuse_level=artifact_reuse_level,
        )
    )
    return state_store, stage


def test_resume_planner_reuses_completed_stage_artifacts(tmp_path: Path) -> None:
    state_store, stage = _seed_stage(
        tmp_path,
        stage_key=StageKey.BUILD,
        stage_status=StageStatus.COMPLETED,
        artifact_reuse_level=ArtifactReuseLevel.REUSABLE,
        next_stage_key=StageKey.VERIFY,
    )

    assessment = RecoveryService(state_store).assess("branch-001", StageKey.BUILD)

    decision = plan_resume_decision(stage=stage, assessment=assessment)

    assert decision.recovery_assessment == "reuse"
    assert decision.resume_stage_iteration == 1
    assert decision.should_publish is False
    assert decision.reusable_artifact_ids == ["build-artifact-001"]
    assert "already has reusable evidence" in decision.message
    assert "continue with verify" in decision.message


def test_resume_planner_surfaces_replay_disposition_for_stale_evidence(tmp_path: Path) -> None:
    state_store, stage = _seed_stage(
        tmp_path,
        stage_key=StageKey.VERIFY,
        stage_status=StageStatus.COMPLETED,
        artifact_reuse_level=ArtifactReuseLevel.REPLAY_REQUIRED,
        next_stage_key=StageKey.SYNTHESIZE,
    )

    assessment = RecoveryService(state_store).assess("branch-001", StageKey.VERIFY)

    decision = plan_resume_decision(stage=stage, assessment=assessment)

    assert decision.recovery_assessment == "replay"
    assert decision.resume_stage_iteration == 2
    assert decision.should_publish is True
    assert decision.replay_artifact_ids == ["verify-artifact-001"]
    assert "needs replay at iteration 2" in decision.message
    assert "stale" in decision.message


def test_resume_planner_surfaces_review_disposition_for_blocked_stage(tmp_path: Path) -> None:
    state_store, stage = _seed_stage(
        tmp_path,
        stage_key=StageKey.VERIFY,
        stage_status=StageStatus.BLOCKED,
        artifact_reuse_level=ArtifactReuseLevel.REUSABLE,
        next_stage_key=StageKey.SYNTHESIZE,
    )

    assessment = RecoveryService(state_store).assess("branch-001", StageKey.VERIFY)

    decision = plan_resume_decision(stage=stage, assessment=assessment)

    assert decision.recovery_assessment == "review"
    assert decision.resume_stage_iteration == 1
    assert decision.should_publish is False
    assert "blocked" in decision.message
    assert "manual review" in decision.message.lower()


def test_rd_code_reuses_completed_stage_instead_of_recomputing(tmp_path: Path) -> None:
    from rd_agent.entry.rd_code import rd_code

    state_store, _ = _seed_stage(
        tmp_path,
        stage_key=StageKey.BUILD,
        stage_status=StageStatus.COMPLETED,
        artifact_reuse_level=ArtifactReuseLevel.REUSABLE,
        next_stage_key=StageKey.VERIFY,
    )

    result = rd_code(
        run_id="run-001",
        branch_id="branch-001",
        summary="Build completed again.",
        artifact_ids=["build-artifact-002"],
        state_store=state_store,
        run_service=RunBoardService(state_store=state_store),
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.BUILD)

    assert result["structuredContent"]["decision"]["recovery_assessment"] == "reuse"
    assert persisted_stage is not None
    assert persisted_stage.stage_iteration == 1
    assert persisted_stage.summary == "build summary"
    assert "already has reusable published evidence" in result["content"][0]["text"]


def test_rd_execute_stops_with_review_when_verify_stage_is_blocked(tmp_path: Path) -> None:
    from rd_agent.entry.rd_execute import rd_execute

    state_store, _ = _seed_stage(
        tmp_path,
        stage_key=StageKey.VERIFY,
        stage_status=StageStatus.BLOCKED,
        artifact_reuse_level=ArtifactReuseLevel.REUSABLE,
        next_stage_key=StageKey.SYNTHESIZE,
    )

    result = rd_execute(
        run_id="run-001",
        branch_id="branch-001",
        summary="Verify rerun requested.",
        artifact_ids=["verify-artifact-002"],
        state_store=state_store,
        run_service=RunBoardService(state_store=state_store),
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.VERIFY)

    assert result["structuredContent"]["decision"]["recovery_assessment"] == "review"
    assert result["structuredContent"]["outcome"] == "review"
    assert persisted_stage is not None
    assert persisted_stage.stage_iteration == 1
    assert "manual review" in result["content"][0]["text"].lower()
