from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rd_agent.contracts.artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from rd_agent.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from rd_agent.contracts.preflight import (
    PreflightBlocker,
    PreflightBlockerCategory,
    PreflightBlockersByCategory,
    PreflightReadiness,
    PreflightResult,
)
from rd_agent.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from rd_agent.contracts.stage import StageKey, StageSnapshot, StageStatus
from rd_agent.contracts.tool_io import RunStartRequest
from rd_agent.entry.rd_agent import route_user_intent
from rd_agent.entry.rd_code import rd_code
from rd_agent.entry.rd_execute import rd_execute
from rd_agent.orchestration.artifact_state_store import ArtifactStateStore
from rd_agent.orchestration.preflight_service import PreflightService
from rd_agent.orchestration.recovery_service import RecoveryService
from rd_agent.orchestration.run_board_service import RunBoardService
from rd_agent.orchestration.skill_loop_service import SkillLoopService
from rd_agent.orchestration.stage_transition_service import StageTransitionService
from rd_agent.ports.execution import ExecutionPort, ExecutionStartResult

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
    artifact_reuse_level: ArtifactReuseLevel = ArtifactReuseLevel.REUSABLE,
) -> ArtifactStateStore:
    state_store = ArtifactStateStore(tmp_path / "state")
    stage = StageSnapshot(
        stage_key=stage_key,
        stage_iteration=1,
        status=stage_status,
        summary=f"{stage_key.value} summary",
        artifact_ids=list(artifact_ids),
        next_stage_key=StageKey.VERIFY if stage_key is StageKey.BUILD else StageKey.SYNTHESIZE,
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
        title="Phase 23",
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
            state_store.write_artifact_snapshot(
                _artifact(
                    artifact_id,
                    branch.branch_id,
                    stage_key,
                    reuse_level=artifact_reuse_level,
                )
            )
    if write_recovery:
        assessment = RecoveryService(state_store).assess("branch-001", stage_key)
        if assessment is None:
            raise AssertionError("expected recovery assessment")
    return state_store


@dataclass
class _DeterministicExecutionPort(ExecutionPort):
    def start_run(self, request: RunStartRequest) -> ExecutionStartResult:
        artifact = _artifact("artifact-framing-001", "branch-001", StageKey.FRAMING)
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
            label=request.initial_branch_label or "primary",
            status=BranchStatus.ACTIVE,
            current_stage_key=StageKey.FRAMING,
            stages=[stage],
            score=BranchScore(
                exploration_priority=1.0,
                result_quality=0.0,
                rationale="Primary branch remains active.",
            ),
            lineage=BranchLineage(source_summary="Created in test state."),
            artifact_ids=[artifact.artifact_id],
        )
        return ExecutionStartResult(branch=branch, stage=stage, artifacts=[artifact])


def test_route_user_intent_keeps_recommended_skill_but_marks_blocked_when_preflight_fails() -> None:
    def _blocked_preflight(_context: dict[str, str]) -> PreflightResult:
        return PreflightResult(
            run_id="run-001",
            branch_id="branch-001",
            stage_key=StageKey.BUILD,
            recommended_next_skill="rd-code",
            readiness=PreflightReadiness.BLOCKED,
            primary_blocker_category=PreflightBlockerCategory.DEPENDENCY,
            primary_blocker_reason="Required dependency pytest is missing.",
            repair_action="Run `uv sync --extra test` before continuing with rd-code.",
            blockers_by_category=PreflightBlockersByCategory(
                dependency=[
                    PreflightBlocker(
                        category=PreflightBlockerCategory.DEPENDENCY,
                        reason="Required dependency pytest is missing.",
                        repair_action="Run `uv sync --extra test` before continuing with rd-code.",
                    )
                ]
            ),
        )

    result = route_user_intent(
        "what should i do next?",
        persisted_state={
            "run": {"run_id": "run-001", "status": "awaiting_operator"},
            "branch": {"branch_id": "branch-001", "status": "paused", "current_stage_key": "build"},
        },
        preflight_result_provider=_blocked_preflight,
    )

    assert result["route_kind"] == "continue_paused_run"
    assert result["recommended_next_skill"] == "rd-code"
    assert result["current_action_status"] == "blocked"
    assert result["current_blocker_category"] == "dependency"
    assert "pytest" in result["current_blocker_reason"]
    assert "uv sync --extra test" in result["repair_action"]
    assert "rd-code" in result["exact_next_action"]
    assert "uv sync --extra test" in result["exact_next_action"]


def test_rd_code_returns_preflight_blocked_without_publishing_stage_transition(tmp_path: Path) -> None:
    state_store = _seed_stage(
        tmp_path,
        stage_key=StageKey.BUILD,
        stage_status=StageStatus.READY,
        artifact_ids=["build-artifact-001"],
        write_artifacts=False,
    )
    run_service = RunBoardService(state_store=state_store)
    transition_service = StageTransitionService(state_store)
    preflight_service = PreflightService(state_store, project_root=REPO_ROOT)

    result = rd_code(
        run_id="run-001",
        branch_id="branch-001",
        summary="Build requested.",
        artifact_ids=["build-artifact-002"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=transition_service,
        preflight_service=preflight_service,
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.BUILD)
    stage_history = state_store.list_stage_snapshots("branch-001", StageKey.BUILD)

    assert result["structuredContent"]["outcome"] == "preflight_blocked"
    assert result["structuredContent"]["preflight"]["primary_blocker_category"] == "artifact"
    assert persisted_stage is not None
    assert persisted_stage.stage_iteration == 1
    assert persisted_stage.summary == "build summary"
    assert len(stage_history) == 1


def test_rd_execute_distinguishes_results_exist_from_environment_reproducible(tmp_path: Path) -> None:
    state_store = _seed_stage(
        tmp_path,
        stage_key=StageKey.VERIFY,
        stage_status=StageStatus.COMPLETED,
        artifact_ids=["verify-artifact-001"],
        write_artifacts=True,
        write_recovery=True,
    )
    run_service = RunBoardService(state_store=state_store)
    transition_service = StageTransitionService(state_store)
    preflight_service = PreflightService(
        state_store,
        project_root=REPO_ROOT,
        module_exists_provider=lambda module_name: module_name not in {"pytest", "import_linter", "importlinter"},
    )

    result = rd_execute(
        run_id="run-001",
        branch_id="branch-001",
        summary="Verify requested.",
        artifact_ids=["verify-artifact-002"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=transition_service,
        preflight_service=preflight_service,
    )

    assert result["structuredContent"]["stage_before"]["artifact_ids"] == ["verify-artifact-001"]
    assert result["structuredContent"]["recovery"] is not None
    assert result["structuredContent"]["outcome"] == "preflight_blocked"
    assert result["structuredContent"]["preflight"]["primary_blocker_category"] == "dependency"
    assert "pytest" in result["structuredContent"]["preflight"]["primary_blocker_reason"]
    assert "uv sync --extra test" in result["structuredContent"]["preflight"]["repair_action"]


def test_skill_loop_ready_summary_does_not_claim_ready_before_preflight(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    branch = BranchSnapshot(
        branch_id="branch-001",
        run_id="run-001",
        label="Primary branch",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.FRAMING,
        stages=[],
        score=BranchScore(
            exploration_priority=0.8,
            result_quality=0.5,
            rationale="Primary branch remains the active path.",
        ),
        lineage=BranchLineage(source_summary="Created in test state."),
        artifact_ids=[],
    )
    run = RunBoardSnapshot(
        run_id="run-001",
        title="Phase 23",
        scenario_label="research",
        status=RunStatus.ACTIVE,
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=3,
        primary_branch_id=branch.branch_id,
        branch_ids=[branch.branch_id],
        highlighted_artifact_ids=[],
        summary="Active run board.",
    )
    state_store.write_run_snapshot(run)
    state_store.write_branch_snapshot(branch)

    service = SkillLoopService(
        state_store=state_store,
        run_service=RunBoardService(state_store=state_store, execution_port=_DeterministicExecutionPort()),
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    service._ensure_stage_exists(
        branch_id="branch-001",
        stage_key=StageKey.BUILD,
        stage_iteration=1,
    )
    build_stage = state_store.load_stage_snapshot("branch-001", StageKey.BUILD)

    assert build_stage is not None
    assert "prepared and requires preflight before execution" in build_stage.summary
    assert "ready" not in build_stage.summary.lower()
