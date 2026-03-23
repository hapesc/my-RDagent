from __future__ import annotations

import ast
from pathlib import Path

import pytest

from v3.contracts.artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import (
    ArtifactListRequest,
    StageBlockRequest,
    StageCompleteRequest,
    StageStartRequest,
    StageTransitionRequest,
)
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.tools.artifact_tools import rd_artifact_list
from v3.tools.stage_write_tools import (
    rd_stage_block,
    rd_stage_complete,
    rd_stage_replay,
    rd_stage_start,
    rd_stage_transition,
)

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORTS = {
    "app.control_plane",
    "app.query_services",
    "app.runtime",
    "core.loop",
    "data_models",
    "service_contracts",
}


def _import_names(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(), filename=str(file_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _artifact(
    artifact_id: str,
    branch_id: str,
    stage_key: StageKey,
    *,
    kind: ArtifactKind = ArtifactKind.PLAN,
    reuse_level: ArtifactReuseLevel = ArtifactReuseLevel.REUSABLE,
) -> ArtifactSnapshot:
    return ArtifactSnapshot(
        artifact_id=artifact_id,
        branch_id=branch_id,
        stage_key=stage_key,
        kind=kind,
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


def _seed_branch(state_store: ArtifactStateStore, *, stage: StageSnapshot) -> BranchSnapshot:
    branch = BranchSnapshot(
        branch_id="branch-001",
        run_id="run-001",
        label="Primary branch",
        status=BranchStatus.ACTIVE,
        current_stage_key=stage.stage_key,
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
    return branch


def _seed_stage_entry_context(
    tmp_path: Path,
) -> tuple[ArtifactStateStore, RunBoardService, RecoveryService, StageTransitionService]:
    state_store = ArtifactStateStore(tmp_path / "state")
    stages = [
        StageSnapshot(
            stage_key=StageKey.FRAMING,
            stage_iteration=1,
            status=StageStatus.READY,
            summary="Framing is ready.",
            artifact_ids=["artifact-framing-ready"],
            next_stage_key=StageKey.BUILD,
        ),
        StageSnapshot(
            stage_key=StageKey.BUILD,
            stage_iteration=1,
            status=StageStatus.READY,
            summary="Build is ready.",
            artifact_ids=["artifact-build-ready"],
            next_stage_key=StageKey.VERIFY,
        ),
        StageSnapshot(
            stage_key=StageKey.VERIFY,
            stage_iteration=1,
            status=StageStatus.READY,
            summary="Verify is ready.",
            artifact_ids=["artifact-verify-ready"],
            next_stage_key=StageKey.SYNTHESIZE,
        ),
        StageSnapshot(
            stage_key=StageKey.SYNTHESIZE,
            stage_iteration=1,
            status=StageStatus.READY,
            summary="Synthesize is ready.",
            artifact_ids=["artifact-synthesize-ready"],
            next_stage_key=None,
        ),
    ]
    branch = BranchSnapshot(
        branch_id="branch-001",
        run_id="run-001",
        label="Primary branch",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.FRAMING,
        stages=list(stages),
        score=BranchScore(
            exploration_priority=0.8,
            result_quality=0.5,
            rationale="Primary branch remains the active path.",
        ),
        lineage=BranchLineage(source_summary="Created in test state."),
        artifact_ids=[artifact_id for stage in stages for artifact_id in stage.artifact_ids],
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
        highlighted_artifact_ids=list(branch.artifact_ids),
        summary="Active run board.",
    )
    state_store.write_run_snapshot(run)
    state_store.write_branch_snapshot(branch)
    for stage in stages:
        state_store.write_stage_snapshot(branch.branch_id, stage)
    for stage in stages:
        for artifact_id in stage.artifact_ids:
            state_store.write_artifact_snapshot(_artifact(artifact_id, branch.branch_id, stage.stage_key))
    return (
        state_store,
        RunBoardService(state_store),
        RecoveryService(state_store),
        StageTransitionService(state_store),
    )


def test_stage_publish_start_and_complete_route_through_canonical_transition_service(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    starting_stage = StageSnapshot(
        stage_key=StageKey.FRAMING,
        stage_iteration=1,
        status=StageStatus.READY,
        summary="Framing is ready.",
        artifact_ids=[],
        next_stage_key=StageKey.BUILD,
    )
    _seed_branch(state_store, stage=starting_stage)

    transition_service = StageTransitionService(state_store)
    start_response = rd_stage_start(
        StageStartRequest(
            branch_id="branch-001",
            stage_key=StageKey.FRAMING,
            stage_iteration=1,
            summary="Framing started.",
            artifact_ids=["artifact-plan"],
            next_stage_key=StageKey.BUILD,
        ),
        service=transition_service,
    )
    complete_response = rd_stage_complete(
        StageCompleteRequest(
            branch_id="branch-001",
            stage_key=StageKey.FRAMING,
            stage_iteration=1,
            summary="Framing completed.",
            artifact_ids=["artifact-plan"],
            next_stage_key=StageKey.BUILD,
        ),
        service=transition_service,
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.FRAMING)
    assert start_response["structuredContent"]["stage"]["status"] == "in_progress"
    assert complete_response["structuredContent"]["stage"]["status"] == "completed"
    assert persisted_stage is not None
    assert persisted_stage.status is StageStatus.COMPLETED
    assert persisted_stage.stage_iteration == 1
    assert state_store.load_branch_snapshot("branch-001").artifact_ids == ["artifact-plan"]  # type: ignore[union-attr]


def test_stage_transition_preserves_replayed_iteration_history_on_branch(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    completed_stage = StageSnapshot(
        stage_key=StageKey.VERIFY,
        stage_iteration=1,
        status=StageStatus.COMPLETED,
        summary="Verify iteration one completed.",
        artifact_ids=["artifact-verify-v1"],
        next_stage_key=StageKey.SYNTHESIZE,
    )
    _seed_branch(state_store, stage=completed_stage)

    response = rd_stage_transition(
        StageTransitionRequest(
            branch_id="branch-001",
            stage_key=StageKey.VERIFY,
            stage_iteration=2,
            status=StageStatus.IN_PROGRESS,
            summary="Verify replay started with refreshed evidence.",
            artifact_ids=["artifact-verify-v2"],
            next_stage_key=StageKey.SYNTHESIZE,
        ),
        service=StageTransitionService(state_store),
    )

    branch = state_store.load_branch_snapshot("branch-001")
    history = state_store.list_stage_snapshots("branch-001", StageKey.VERIFY)

    assert response["structuredContent"]["stage"]["stage_iteration"] == 2
    assert branch is not None
    assert [(item.stage_key, item.stage_iteration) for item in branch.stages] == [
        (StageKey.VERIFY, 1),
        (StageKey.VERIFY, 2),
    ]
    assert [item.stage_iteration for item in history] == [1, 2]


def test_stage_replay_publishes_in_progress_iteration_with_replay_language(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    completed_stage = StageSnapshot(
        stage_key=StageKey.BUILD,
        stage_iteration=1,
        status=StageStatus.COMPLETED,
        summary="Build iteration one completed.",
        artifact_ids=["artifact-build-v1"],
        next_stage_key=StageKey.VERIFY,
    )
    _seed_branch(state_store, stage=completed_stage)

    response = rd_stage_replay(
        StageStartRequest(
            branch_id="branch-001",
            stage_key=StageKey.BUILD,
            stage_iteration=2,
            summary="Build replay started with refreshed inputs.",
            artifact_ids=["artifact-build-v2"],
            next_stage_key=StageKey.VERIFY,
        ),
        service=StageTransitionService(state_store),
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.BUILD)
    history = state_store.list_stage_snapshots("branch-001", StageKey.BUILD)

    assert response["structuredContent"]["stage"]["status"] == "in_progress"
    assert response["structuredContent"]["stage"]["stage_iteration"] == 2
    assert "replay" in response["content"][0]["text"]
    assert persisted_stage is not None
    assert persisted_stage.stage_iteration == 2
    assert [item.stage_iteration for item in history] == [1, 2]


def test_stage_publish_block_reports_v3_blocking_truth(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    verify_stage = StageSnapshot(
        stage_key=StageKey.VERIFY,
        stage_iteration=1,
        status=StageStatus.IN_PROGRESS,
        summary="Verify is running.",
        artifact_ids=["artifact-verify"],
        next_stage_key=StageKey.SYNTHESIZE,
    )
    _seed_branch(state_store, stage=verify_stage)

    response = rd_stage_block(
        StageBlockRequest(
            branch_id="branch-001",
            stage_key=StageKey.VERIFY,
            stage_iteration=1,
            summary="Verify is blocked pending refreshed evidence.",
            artifact_ids=["artifact-verify"],
            blocking_reasons=["Regression evidence is stale."],
            next_stage_key=StageKey.SYNTHESIZE,
        ),
        service=StageTransitionService(state_store),
    )

    assert response["structuredContent"]["stage"]["status"] == "blocked"
    assert response["structuredContent"]["stage"]["blocking_reasons"] == ["Regression evidence is stale."]
    assert "blocked" in response["content"][0]["text"]


def test_importlinter_extends_forbidden_imports_to_stage_write_tools() -> None:
    config = Path(".importlinter").read_text()

    assert "v3.tools.stage_write_tools" in config
    assert "app.control_plane" in config
    assert "app.query_services" in config
    assert "app.runtime" in config
    assert "service_contracts" in config
    assert "data_models" in config
    assert "core.loop" in config


def test_rd_propose_completes_framing_stage_via_v3_tools_only(tmp_path: Path) -> None:
    from v3.entry.rd_propose import rd_propose

    state_store, run_service, recovery_service, transition_service = _seed_stage_entry_context(tmp_path)

    response = rd_propose(
        run_id="run-001",
        branch_id="branch-001",
        summary="Framing completed with a concrete plan.",
        artifact_ids=["artifact-plan-v2"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.FRAMING)
    artifact_response = rd_artifact_list(
        ArtifactListRequest(run_id="run-001", branch_id="branch-001", stage_key=StageKey.FRAMING),
        state_store=state_store,
    )

    assert response["structuredContent"]["owned_stage"] == "framing"
    assert response["structuredContent"]["stage_after"]["status"] == "completed"
    assert response["structuredContent"]["stage_after"]["next_stage_key"] == "build"
    assert response["structuredContent"]["artifacts_before"][0]["artifact_id"] == "artifact-framing-ready"
    assert persisted_stage is not None
    assert persisted_stage.status is StageStatus.COMPLETED
    assert persisted_stage.artifact_ids == ["artifact-plan-v2"]
    assert artifact_response["structuredContent"]["items"][0]["artifact_id"] == "artifact-framing-ready"


def test_rd_code_completes_build_stage_via_v3_tools_only(tmp_path: Path) -> None:
    from v3.entry.rd_code import rd_code

    state_store, run_service, recovery_service, transition_service = _seed_stage_entry_context(tmp_path)

    response = rd_code(
        run_id="run-001",
        branch_id="branch-001",
        summary="Build completed with updated code evidence.",
        artifact_ids=["artifact-code-v2"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.BUILD)

    assert response["structuredContent"]["owned_stage"] == "build"
    assert response["structuredContent"]["stage_after"]["status"] == "completed"
    assert response["structuredContent"]["stage_after"]["next_stage_key"] == "verify"
    assert response["structuredContent"]["artifacts_before"][0]["artifact_id"] == "artifact-build-ready"
    assert persisted_stage is not None
    assert persisted_stage.status is StageStatus.COMPLETED
    assert persisted_stage.artifact_ids == ["artifact-code-v2"]


def test_v3_entry_exports_propose_and_code_stage_entrypoints() -> None:
    from v3.entry import __all__ as exported_names

    assert "rd_propose" in exported_names
    assert "rd_code" in exported_names
    assert "rd_execute" in exported_names
    assert "rd_evaluate" in exported_names


def test_rd_execute_publishes_verify_completion_when_unblocked(tmp_path: Path) -> None:
    from v3.entry.rd_execute import rd_execute

    state_store, run_service, recovery_service, transition_service = _seed_stage_entry_context(tmp_path)

    response = rd_execute(
        run_id="run-001",
        branch_id="branch-001",
        summary="Verify completed with fresh execution evidence.",
        artifact_ids=["artifact-verify-v2"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.VERIFY)

    assert response["structuredContent"]["owned_stage"] == "verify"
    assert response["structuredContent"]["outcome"] == "completed"
    assert response["structuredContent"]["stage_after"]["status"] == "completed"
    assert response["structuredContent"]["stage_after"]["next_stage_key"] == "synthesize"
    assert persisted_stage is not None
    assert persisted_stage.status is StageStatus.COMPLETED
    assert persisted_stage.artifact_ids == ["artifact-verify-v2"]


def test_rd_execute_publishes_verify_blocker_when_reasons_present(tmp_path: Path) -> None:
    from v3.entry.rd_execute import rd_execute

    state_store, run_service, recovery_service, transition_service = _seed_stage_entry_context(tmp_path)

    response = rd_execute(
        run_id="run-001",
        branch_id="branch-001",
        summary="Verify is blocked pending refreshed regression evidence.",
        artifact_ids=["artifact-verify-v2"],
        blocking_reasons=["Regression evidence is stale."],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.VERIFY)

    assert response["structuredContent"]["owned_stage"] == "verify"
    assert response["structuredContent"]["outcome"] == "blocked"
    assert response["structuredContent"]["stage_after"]["status"] == "blocked"
    assert response["structuredContent"]["stage_after"]["blocking_reasons"] == ["Regression evidence is stale."]
    assert persisted_stage is not None
    assert persisted_stage.status is StageStatus.BLOCKED


def test_rd_evaluate_publishes_synthesis_summary_and_recommendation(tmp_path: Path) -> None:
    from v3.entry.rd_evaluate import rd_evaluate

    state_store, run_service, recovery_service, transition_service = _seed_stage_entry_context(tmp_path)

    response = rd_evaluate(
        run_id="run-001",
        branch_id="branch-001",
        summary="Synthesis completed with a recommendation to continue.",
        artifact_ids=["artifact-summary-v2"],
        recommendation="continue",
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )

    persisted_stage = state_store.load_stage_snapshot("branch-001", StageKey.SYNTHESIZE)

    assert response["structuredContent"]["owned_stage"] == "synthesize"
    assert response["structuredContent"]["recommendation"] == "continue"
    assert response["structuredContent"]["stage_after"]["status"] == "completed"
    assert response["structuredContent"]["stage_after"]["next_stage_key"] == "framing"
    assert persisted_stage is not None
    assert persisted_stage.status is StageStatus.COMPLETED
    assert persisted_stage.artifact_ids == ["artifact-summary-v2"]


def test_stage_entrypoints_are_independently_invokable_against_same_branch(tmp_path: Path) -> None:
    from v3.entry.rd_code import rd_code
    from v3.entry.rd_evaluate import rd_evaluate
    from v3.entry.rd_execute import rd_execute
    from v3.entry.rd_propose import rd_propose

    state_store, run_service, recovery_service, transition_service = _seed_stage_entry_context(tmp_path)

    propose_response = rd_propose(
        run_id="run-001",
        branch_id="branch-001",
        summary="Framing completed independently.",
        artifact_ids=["artifact-plan-independent"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )
    code_response = rd_code(
        run_id="run-001",
        branch_id="branch-001",
        summary="Build completed independently.",
        artifact_ids=["artifact-code-independent"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )
    execute_response = rd_execute(
        run_id="run-001",
        branch_id="branch-001",
        summary="Verify completed independently.",
        artifact_ids=["artifact-verify-independent"],
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )
    evaluate_response = rd_evaluate(
        run_id="run-001",
        branch_id="branch-001",
        summary="Synthesize completed independently.",
        artifact_ids=["artifact-summary-independent"],
        recommendation="stop",
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )

    assert propose_response["structuredContent"]["owned_stage"] == "framing"
    assert code_response["structuredContent"]["owned_stage"] == "build"
    assert execute_response["structuredContent"]["owned_stage"] == "verify"
    assert evaluate_response["structuredContent"]["owned_stage"] == "synthesize"
    assert evaluate_response["structuredContent"]["recommendation"] == "stop"
    assert evaluate_response["structuredContent"]["stage_after"]["next_stage_key"] is None


@pytest.mark.parametrize(
    "relative_path",
    [
        "v3/entry/rd_propose.py",
        "v3/entry/rd_code.py",
        "v3/entry/rd_execute.py",
        "v3/entry/rd_evaluate.py",
    ],
)
def test_stage_entry_modules_avoid_legacy_runtime_imports(relative_path: str) -> None:
    imports = _import_names(ROOT / relative_path)
    violations = sorted(
        name
        for name in imports
        if any(name == forbidden or name.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_IMPORTS)
    )
    assert violations == []
