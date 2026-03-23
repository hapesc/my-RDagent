from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from v3.contracts.artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus, RunStopReason
from v3.contracts.tool_io import RunStartRequest
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.ports.execution import ExecutionPort, ExecutionStartResult


def test_run_contract_exposes_execution_mode_iteration_ceiling_and_stop_reason() -> None:
    run = RunBoardSnapshot(
        run_id="run-001",
        title="Skills-first loop",
        scenario_label="data_science",
        status=RunStatus.PAUSED,
        primary_branch_id="branch-001",
        branch_ids=["branch-001"],
        highlighted_artifact_ids=["artifact-001"],
        summary="Paused after verify for operator review.",
        current_stage_iteration=3,
        execution_mode=ExecutionMode.GATED,
        max_stage_iterations=3,
        completed_stage_iterations=2,
        stop_reason=RunStopReason.AWAITING_OPERATOR,
    )

    public_dump = run.model_dump(mode="json")

    assert public_dump["current_stage_iteration"] == 3
    assert public_dump["execution_mode"] == "gated"
    assert public_dump["max_stage_iterations"] == 3
    assert public_dump["completed_stage_iterations"] == 2
    assert public_dump["stop_reason"] == "awaiting_operator"


def test_run_start_request_accepts_public_execution_policy_controls() -> None:
    request = RunStartRequest(
        title="Loop run",
        task_summary="Work through framing/build/verify/synthesize until bounded stop.",
        scenario_label="research",
        initial_branch_label="primary",
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=4,
    )

    assert request.execution_mode is ExecutionMode.UNATTENDED
    assert request.max_stage_iterations == 4


def test_stage_contract_is_iteration_aware_in_public_v3_terms() -> None:
    stage = StageSnapshot(
        stage_key=StageKey.VERIFY,
        status=StageStatus.BLOCKED,
        summary="Verification needs refreshed evidence.",
        artifact_ids=["artifact-verify"],
        blocking_reasons=["Regression evidence is stale."],
        next_stage_key=StageKey.SYNTHESIZE,
        stage_iteration=2,
    )

    public_dump = stage.model_dump(mode="json")

    assert public_dump["stage_iteration"] == 2
    assert "checkpoint" not in str(public_dump)
    assert "node" not in str(public_dump)


def test_iteration_persistence_keeps_latest_snapshot_and_history(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    first = StageSnapshot(
        stage_key=StageKey.FRAMING,
        status=StageStatus.COMPLETED,
        summary="Initial framing iteration completed.",
        artifact_ids=["artifact-plan-v1"],
        next_stage_key=StageKey.BUILD,
        stage_iteration=1,
    )
    second = StageSnapshot(
        stage_key=StageKey.FRAMING,
        status=StageStatus.COMPLETED,
        summary="Refined framing iteration completed.",
        artifact_ids=["artifact-plan-v2"],
        next_stage_key=StageKey.BUILD,
        stage_iteration=2,
    )

    state_store.write_stage_snapshot("branch-001", first)
    state_store.write_stage_snapshot("branch-001", second)

    latest = state_store.load_stage_snapshot("branch-001", StageKey.FRAMING)
    first_iteration = state_store.load_stage_snapshot("branch-001", StageKey.FRAMING, stage_iteration=1)
    history = state_store.list_stage_snapshots("branch-001", StageKey.FRAMING)

    assert latest == second
    assert first_iteration == first
    assert [item.stage_iteration for item in history] == [1, 2]
    assert history[0].artifact_ids == ["artifact-plan-v1"]
    assert history[1].artifact_ids == ["artifact-plan-v2"]


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


def test_execution_policy_returns_v3_pause_and_ceiling_decisions() -> None:
    from v3.orchestration.execution_policy import AgentExecutionPolicy, evaluate_stage_boundary

    gated_decision = evaluate_stage_boundary(
        policy=AgentExecutionPolicy(mode=ExecutionMode.GATED, max_stage_iterations=2),
        current_iteration=1,
        stage_key=StageKey.FRAMING,
        stage_status=StageStatus.COMPLETED,
        next_stage_key=StageKey.BUILD,
    )
    ceiling_decision = evaluate_stage_boundary(
        policy=AgentExecutionPolicy(mode=ExecutionMode.UNATTENDED, max_stage_iterations=1),
        current_iteration=1,
        stage_key=StageKey.SYNTHESIZE,
        stage_status=StageStatus.COMPLETED,
        next_stage_key=StageKey.FRAMING,
        recommendation="continue",
    )

    assert gated_decision.should_stop is True
    assert gated_decision.run_status is RunStatus.PAUSED
    assert gated_decision.stop_reason is RunStopReason.AWAITING_OPERATOR
    assert "operator review" in gated_decision.message.lower()
    assert "checkpoint" not in gated_decision.message.lower()
    assert ceiling_decision.should_stop is True
    assert ceiling_decision.stop_reason is RunStopReason.ITERATION_CEILING_REACHED
    assert ceiling_decision.run_status is RunStatus.PAUSED
    assert "hard iteration ceiling of 1" in ceiling_decision.message.lower()
    assert "node" not in ceiling_decision.message.lower()


def test_rd_agent_gated_mode_pauses_at_stage_boundary_and_persists_stop_reason(tmp_path: Path) -> None:
    from v3.entry.rd_agent import rd_agent

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(
        state_store=state_store,
        execution_port=_DeterministicExecutionPort(),
    )

    result = rd_agent(
        title="Phase 14 gated task",
        task_summary="Pause after the first completed stage for review.",
        scenario_label="research",
        initial_branch_label="primary",
        execution_mode=ExecutionMode.GATED,
        max_stage_iterations=2,
        stage_inputs={
            StageKey.FRAMING: {
                "summary": "Framing completed with a concrete plan.",
                "artifact_ids": ["artifact-framing-001"],
            },
        },
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    run = state_store.load_run_snapshot("run-001")
    build_stage = state_store.load_stage_snapshot("branch-001", StageKey.BUILD)

    assert result["structuredContent"]["stop_reason"] == "awaiting_operator"
    assert [item["stage_key"] for item in result["structuredContent"]["history"]] == ["framing"]
    assert run is not None
    assert run.status is RunStatus.PAUSED
    assert run.stop_reason is RunStopReason.AWAITING_OPERATOR
    assert run.current_stage_iteration == 1
    assert run.completed_stage_iterations == 0
    assert build_stage is not None
    assert build_stage.status is StageStatus.NOT_STARTED
    assert build_stage.summary == "Prepared and requires preflight before execution."
    assert "paused after framing" in result["content"][0]["text"].lower()
    assert "operator review" in result["content"][0]["text"].lower()


def test_rd_agent_unattended_mode_enforces_hard_iteration_ceiling(tmp_path: Path) -> None:
    from v3.entry.rd_agent import rd_agent

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(
        state_store=state_store,
        execution_port=_DeterministicExecutionPort(),
    )

    result = rd_agent(
        title="Phase 14 unattended task",
        task_summary="Continue until the hard iteration ceiling requires a stop.",
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
                "summary": "Synthesize concluded another iteration would help.",
                "artifact_ids": ["artifact-synthesize-001"],
                "recommendation": "continue",
            },
        },
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    run = state_store.load_run_snapshot("run-001")
    next_framing = state_store.load_stage_snapshot("branch-001", StageKey.FRAMING, stage_iteration=2)

    assert result["structuredContent"]["stop_reason"] == "iteration_ceiling_reached"
    assert [item["stage_key"] for item in result["structuredContent"]["history"]] == [
        "framing",
        "build",
        "verify",
        "synthesize",
    ]
    assert run is not None
    assert run.status is RunStatus.PAUSED
    assert run.stop_reason is RunStopReason.ITERATION_CEILING_REACHED
    assert run.completed_stage_iterations == 1
    assert run.current_stage_iteration == 2
    assert next_framing is None
    assert "hard iteration ceiling of 1" in result["content"][0]["text"].lower()
