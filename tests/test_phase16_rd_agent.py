from __future__ import annotations

from dataclasses import dataclass

from v3.contracts.artifact import ArtifactKind, ArtifactLocator, ArtifactProvenance, ArtifactReuseLevel, ArtifactSnapshot
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.run import ExecutionMode
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


def test_rd_agent_dispatches_parallel_exploration_subagents_with_isolated_workspaces(tmp_path) -> None:
    from v3.entry.rd_agent import rd_agent

    dispatches: list[dict[str, str]] = []

    def _dispatcher(payload):
        dispatches.append(payload)
        return payload

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(state_store=state_store, execution_port=_DeterministicExecutionPort())

    rd_agent(
        title="Phase 16 task",
        task_summary="Drive multi-branch exploration.",
        scenario_label="research",
        initial_branch_label="primary",
        branch_hypotheses=["primary", "alt-a", "alt-b"],
        dispatcher=_dispatcher,
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=1,
        stage_inputs={
            StageKey.FRAMING: {"summary": "Framing complete.", "artifact_ids": ["artifact-framing-001"]},
            StageKey.BUILD: {"summary": "Build complete.", "artifact_ids": ["artifact-build-001"]},
            StageKey.VERIFY: {"summary": "Verify complete.", "artifact_ids": ["artifact-verify-001"]},
            StageKey.SYNTHESIZE: {"summary": "Synthesize complete.", "artifact_ids": ["artifact-synthesize-001"], "recommendation": "stop"},
        },
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    assert len(dispatches) == 3
    assert len({payload["branch_id"] for payload in dispatches}) == 3
    assert all(payload["workspace_root"].endswith("workspace") for payload in dispatches)


def test_rd_agent_runs_multi_branch_explore_and_converge_round(tmp_path) -> None:
    from v3.entry.rd_agent import rd_agent

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(state_store=state_store, execution_port=_DeterministicExecutionPort())

    result = rd_agent(
        title="Phase 16 task",
        task_summary="Drive multi-branch exploration.",
        scenario_label="research",
        initial_branch_label="primary",
        branch_hypotheses=["primary", "alt-a", "alt-b"],
        dispatcher=lambda payload: payload,
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=1,
        stage_inputs={
            StageKey.FRAMING: {"summary": "Framing complete.", "artifact_ids": ["artifact-framing-001"]},
            StageKey.BUILD: {"summary": "Build complete.", "artifact_ids": ["artifact-build-001"]},
            StageKey.VERIFY: {"summary": "Verify complete.", "artifact_ids": ["artifact-verify-001"]},
            StageKey.SYNTHESIZE: {"summary": "Synthesize complete.", "artifact_ids": ["artifact-synthesize-001"], "recommendation": "stop"},
        },
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    assert result["structuredContent"]["selected_branch_id"].startswith("branch-")
    assert result["structuredContent"]["board"]["mode"] in {"exploration", "convergence"}
    assert result["structuredContent"]["merge_summary"]


def test_rd_agent_reports_branch_board_mode_and_recommended_next_step(tmp_path) -> None:
    from v3.entry.rd_agent import rd_agent

    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(state_store=state_store, execution_port=_DeterministicExecutionPort())

    result = rd_agent(
        title="Phase 16 task",
        task_summary="Drive multi-branch exploration.",
        scenario_label="research",
        initial_branch_label="primary",
        branch_hypotheses=["primary", "alt-a"],
        dispatcher=lambda payload: payload,
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=1,
        stage_inputs={
            StageKey.FRAMING: {"summary": "Framing complete.", "artifact_ids": ["artifact-framing-001"]},
            StageKey.BUILD: {"summary": "Build complete.", "artifact_ids": ["artifact-build-001"]},
            StageKey.VERIFY: {"summary": "Verify complete.", "artifact_ids": ["artifact-verify-001"]},
            StageKey.SYNTHESIZE: {"summary": "Synthesize complete.", "artifact_ids": ["artifact-synthesize-001"], "recommendation": "stop"},
        },
        state_store=state_store,
        run_service=run_service,
        recovery_service=RecoveryService(state_store),
        transition_service=StageTransitionService(state_store),
    )

    assert result["structuredContent"]["mode"] in {"exploration", "convergence"}
    assert result["structuredContent"]["recommended_next_step"]
    assert "Multi-branch round explored" in result["content"][0]["text"]
