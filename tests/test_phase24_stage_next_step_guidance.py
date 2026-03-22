from __future__ import annotations

from pathlib import Path

from v3.contracts.artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.recovery import RecoveryAssessment, RecoveryDisposition
from v3.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.preflight_service import PreflightService
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.resume_planner import plan_resume_decision
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.entry.rd_propose import rd_propose
from v3.entry.rd_code import rd_code
from v3.entry.rd_execute import rd_execute
from v3.entry.rd_evaluate import rd_evaluate

REPO_ROOT = Path(__file__).resolve().parents[1]


def _artifact(
    artifact_id: str,
    branch_id: str,
    stage_key: StageKey,
    *,
    reuse_level: ArtifactReuseLevel = ArtifactReuseLevel.REUSABLE,
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
    artifact_ids: list[str],
    write_artifacts: bool = True,
    write_recovery: bool = False,
) -> ArtifactStateStore:
    state_store = ArtifactStateStore(tmp_path / "state")
    next_stage_map = {
        StageKey.FRAMING: StageKey.BUILD,
        StageKey.BUILD: StageKey.VERIFY,
        StageKey.VERIFY: StageKey.SYNTHESIZE,
        StageKey.SYNTHESIZE: None,
    }
    stage = StageSnapshot(
        stage_key=stage_key,
        stage_iteration=1,
        status=stage_status,
        summary=f"{stage_key.value} summary",
        artifact_ids=list(artifact_ids),
        next_stage_key=next_stage_map[stage_key],
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
        artifact_ids=list(artifact_ids),
    )
    run = RunBoardSnapshot(
        run_id="run-001",
        title="Phase 24",
        scenario_label="research",
        status=RunStatus.ACTIVE,
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=3,
        primary_branch_id=branch.branch_id,
        branch_ids=[branch.branch_id],
        highlighted_artifact_ids=list(artifact_ids),
        summary="Active run board.",
    )
    state_store.write_run_snapshot(run)
    state_store.write_branch_snapshot(branch)
    state_store.write_stage_snapshot(branch.branch_id, stage)
    if write_artifacts:
        for artifact_id in artifact_ids:
            state_store.write_artifact_snapshot(_artifact(artifact_id, branch.branch_id, stage_key))
    if write_recovery:
        assessment = RecoveryService(state_store).assess("branch-001", stage_key)
        if assessment is None:
            raise AssertionError("expected recovery assessment")
    return state_store


def _services(state_store: ArtifactStateStore):
    return (
        RunBoardService(state_store=state_store),
        RecoveryService(state_store),
        StageTransitionService(state_store),
    )


def _assert_three_part_text(text: str) -> None:
    assert "Current state:" in text
    assert "Reason:" in text
    assert "Next action:" in text


def test_rd_propose_completed_guidance_points_to_rd_code(tmp_path: Path) -> None:
    state_store = _seed_stage(
        tmp_path,
        stage_key=StageKey.FRAMING,
        stage_status=StageStatus.READY,
        artifact_ids=["framing-artifact-001"],
    )
    run_service, recovery_service, transition_service = _services(state_store)

    result = rd_propose(
        run_id="run-001",
        branch_id="branch-001",
        summary="Framing requested.",
        artifact_ids=["framing-artifact-002"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
        preflight_service=PreflightService(state_store, project_root=REPO_ROOT),
    )

    assert result["structuredContent"]["operator_guidance"]["recommended_next_skill"] == "rd-code"
    _assert_three_part_text(result["content"][0]["text"])


def test_rd_code_preflight_blocked_returns_operator_guidance_with_repair_first_order(tmp_path: Path) -> None:
    state_store = _seed_stage(
        tmp_path,
        stage_key=StageKey.BUILD,
        stage_status=StageStatus.READY,
        artifact_ids=["build-artifact-001"],
        write_artifacts=False,
    )
    run_service, recovery_service, transition_service = _services(state_store)

    result = rd_code(
        run_id="run-001",
        branch_id="branch-001",
        summary="Build requested.",
        artifact_ids=["build-artifact-002"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
        preflight_service=PreflightService(state_store, project_root=REPO_ROOT),
    )

    guidance = result["structuredContent"]["operator_guidance"]
    assert result["structuredContent"]["outcome"] == "preflight_blocked"
    assert guidance["recommended_next_skill"] == "rd-code"
    assert guidance["exact_next_action"].index("repair") < guidance["exact_next_action"].index("continue")
    _assert_three_part_text(result["content"][0]["text"])


def test_rd_code_completed_guidance_points_to_rd_execute(tmp_path: Path) -> None:
    state_store = _seed_stage(
        tmp_path,
        stage_key=StageKey.BUILD,
        stage_status=StageStatus.READY,
        artifact_ids=["build-artifact-001"],
    )
    run_service, recovery_service, transition_service = _services(state_store)

    result = rd_code(
        run_id="run-001",
        branch_id="branch-001",
        summary="Build requested.",
        artifact_ids=["build-artifact-002"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
        preflight_service=PreflightService(state_store, project_root=REPO_ROOT),
    )

    assert result["structuredContent"]["operator_guidance"]["recommended_next_skill"] == "rd-execute"
    _assert_three_part_text(result["content"][0]["text"])


def test_rd_execute_completed_guidance_points_to_rd_evaluate(tmp_path: Path) -> None:
    state_store = _seed_stage(
        tmp_path,
        stage_key=StageKey.VERIFY,
        stage_status=StageStatus.READY,
        artifact_ids=["verify-artifact-001"],
    )
    run_service, recovery_service, transition_service = _services(state_store)

    result = rd_execute(
        run_id="run-001",
        branch_id="branch-001",
        summary="Verify requested.",
        artifact_ids=["verify-artifact-002"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
        preflight_service=PreflightService(state_store, project_root=REPO_ROOT),
    )

    assert result["structuredContent"]["operator_guidance"]["recommended_next_skill"] == "rd-evaluate"
    _assert_three_part_text(result["content"][0]["text"])


def test_rd_execute_blocked_verification_guidance_stays_out_of_normal_handoff(tmp_path: Path) -> None:
    state_store = _seed_stage(
        tmp_path,
        stage_key=StageKey.VERIFY,
        stage_status=StageStatus.READY,
        artifact_ids=["verify-artifact-001"],
    )
    run_service, recovery_service, transition_service = _services(state_store)

    result = rd_execute(
        run_id="run-001",
        branch_id="branch-001",
        summary="Verify requested.",
        artifact_ids=["verify-artifact-002"],
        blocking_reasons=["Tests failed."],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
        preflight_service=PreflightService(state_store, project_root=REPO_ROOT),
    )

    guidance = result["structuredContent"]["operator_guidance"]
    assert result["structuredContent"]["outcome"] == "blocked"
    assert guidance["recommended_next_skill"] == "rd-execute"
    assert "rd-evaluate" not in guidance["exact_next_action"]
    _assert_three_part_text(result["content"][0]["text"])


def test_rd_evaluate_continue_guidance_points_to_rd_propose(tmp_path: Path) -> None:
    state_store = _seed_stage(
        tmp_path,
        stage_key=StageKey.SYNTHESIZE,
        stage_status=StageStatus.READY,
        artifact_ids=["synthesize-artifact-001"],
    )
    run_service, recovery_service, transition_service = _services(state_store)

    result = rd_evaluate(
        run_id="run-001",
        branch_id="branch-001",
        summary="Synthesize requested.",
        artifact_ids=["synthesize-artifact-002"],
        recommendation="continue",
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
        preflight_service=PreflightService(state_store, project_root=REPO_ROOT),
    )

    assert result["structuredContent"]["operator_guidance"]["recommended_next_skill"] == "rd-propose"
    _assert_three_part_text(result["content"][0]["text"])


def test_rd_evaluate_stop_guidance_reports_no_next_stage_skill(tmp_path: Path) -> None:
    state_store = _seed_stage(
        tmp_path,
        stage_key=StageKey.SYNTHESIZE,
        stage_status=StageStatus.READY,
        artifact_ids=["synthesize-artifact-001"],
    )
    run_service, recovery_service, transition_service = _services(state_store)

    result = rd_evaluate(
        run_id="run-001",
        branch_id="branch-001",
        summary="Synthesize requested.",
        artifact_ids=["synthesize-artifact-002"],
        recommendation="stop",
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
        preflight_service=PreflightService(state_store, project_root=REPO_ROOT),
    )

    guidance = result["structuredContent"]["operator_guidance"]
    assert "no next stage skill" in guidance["exact_next_action"].lower()
    _assert_three_part_text(result["content"][0]["text"])


def test_resume_planner_messages_follow_current_state_reason_next_action_shape() -> None:
    review_stage = StageSnapshot(
        stage_key=StageKey.VERIFY,
        stage_iteration=1,
        status=StageStatus.BLOCKED,
        summary="Verify summary",
        artifact_ids=["verify-artifact-001"],
        blocking_reasons=["Tests failed."],
        next_stage_key=StageKey.SYNTHESIZE,
    )
    review_decision = plan_resume_decision(stage=review_stage, assessment=None)

    reuse_assessment = RecoveryAssessment(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=StageKey.BUILD,
        disposition=RecoveryDisposition.REUSE,
        reusable_artifact_ids=["build-artifact-001"],
        replay_artifact_ids=[],
        invalid_reasons=[],
        recommended_next_step="continue with rd-code",
    )
    reuse_stage = StageSnapshot(
        stage_key=StageKey.BUILD,
        stage_iteration=1,
        status=StageStatus.COMPLETED,
        summary="Build summary",
        artifact_ids=["build-artifact-001"],
        next_stage_key=StageKey.VERIFY,
    )
    reuse_decision = plan_resume_decision(stage=reuse_stage, assessment=reuse_assessment)

    _assert_three_part_text(review_decision.message)
    _assert_three_part_text(reuse_decision.message)
