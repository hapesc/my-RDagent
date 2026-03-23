from __future__ import annotations

import ast
import sys
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
from v3.contracts.recovery import (
    RecoveryAssessment,
    RecoveryDisposition,
    RecoveryReasonCode,
)
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import (
    ArtifactListRequest,
    ArtifactListResult,
    BranchGetRequest,
    BranchGetResult,
    BranchListRequest,
    BranchListResult,
    BranchPathsGetRequest,
    BranchPathsGetResult,
    MemoryCreateRequest,
    MemoryGetRequest,
    MemoryGetResult,
    MemoryListRequest,
    MemoryListResult,
    MemoryPromoteRequest,
    RecoveryAssessRequest,
    RecoveryAssessResult,
    RunGetRequest,
    RunGetResult,
    RunStartRequest,
    StageGetRequest,
    StageGetResult,
)
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.ports.execution import ExecutionStartResult

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


def _branch(branch_id: str, run_id: str, stage: StageSnapshot, artifact_ids: list[str]) -> BranchSnapshot:
    return BranchSnapshot(
        branch_id=branch_id,
        run_id=run_id,
        label=f"{branch_id} label",
        status=BranchStatus.ACTIVE,
        current_stage_key=stage.stage_key,
        stages=[stage],
        score=BranchScore(
            exploration_priority=0.7,
            result_quality=0.4,
            rationale=f"{branch_id} remains the leading branch.",
        ),
        lineage=BranchLineage(source_summary="Created in test state."),
        artifact_ids=artifact_ids,
    )


class SpyExecutionPort:
    def __init__(self) -> None:
        self.requests: list[RunStartRequest] = []

    def start_run(self, request: RunStartRequest) -> ExecutionStartResult:
        self.requests.append(request)
        stage = StageSnapshot(
            stage_key=StageKey.FRAMING,
            status=StageStatus.IN_PROGRESS,
            summary="Framing started.",
            artifact_ids=["artifact-start"],
            next_stage_key=StageKey.BUILD,
        )
        artifact = _artifact(
            "artifact-start",
            "branch-start",
            StageKey.FRAMING,
            reuse_level=ArtifactReuseLevel.REFERENCE,
        )
        return ExecutionStartResult(
            branch=_branch("branch-start", "run-start", stage, [artifact.artifact_id]),
            stage=stage,
            artifacts=[artifact],
        )


def _seed_run_state(state_store: ArtifactStateStore) -> tuple[BranchSnapshot, BranchSnapshot, ArtifactSnapshot, ArtifactSnapshot]:
    framing_stage = StageSnapshot(
        stage_key=StageKey.FRAMING,
        status=StageStatus.COMPLETED,
        summary="Framing completed.",
        artifact_ids=["artifact-framing"],
        next_stage_key=StageKey.BUILD,
    )
    build_stage = StageSnapshot(
        stage_key=StageKey.BUILD,
        status=StageStatus.IN_PROGRESS,
        summary="Build in progress.",
        artifact_ids=["artifact-build"],
        next_stage_key=StageKey.VERIFY,
    )
    primary_branch = _branch("branch-001", "run-001", framing_stage, ["artifact-framing"])
    secondary_branch = _branch("branch-002", "run-001", build_stage, ["artifact-build"])
    completed_branch = secondary_branch.model_copy(update={"status": BranchStatus.COMPLETED})
    framing_artifact = _artifact("artifact-framing", primary_branch.branch_id, StageKey.FRAMING)
    build_artifact = _artifact("artifact-build", completed_branch.branch_id, StageKey.BUILD, kind=ArtifactKind.CODE)

    from v3.contracts.run import RunBoardSnapshot, RunStatus

    state_store.write_branch_snapshot(primary_branch)
    state_store.write_branch_snapshot(completed_branch)
    state_store.write_stage_snapshot(primary_branch.branch_id, framing_stage)
    state_store.write_stage_snapshot(completed_branch.branch_id, build_stage)
    state_store.write_artifact_snapshot(framing_artifact)
    state_store.write_artifact_snapshot(build_artifact)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-001",
            title="Boundary reset",
            scenario_label="data_science",
            status=RunStatus.ACTIVE,
            primary_branch_id=primary_branch.branch_id,
            branch_ids=[primary_branch.branch_id, completed_branch.branch_id],
            highlighted_artifact_ids=[framing_artifact.artifact_id],
            summary="Run board summary.",
        )
    )
    return primary_branch, completed_branch, framing_artifact, build_artifact


def _seed_recovery_state(state_store: ArtifactStateStore) -> ArtifactSnapshot:
    verify_stage = StageSnapshot(
        stage_key=StageKey.VERIFY,
        status=StageStatus.BLOCKED,
        summary="Verification is blocked.",
        artifact_ids=["artifact-verify"],
        blocking_reasons=["Regression evidence is stale."],
        next_stage_key=StageKey.SYNTHESIZE,
    )
    branch = BranchSnapshot(
        branch_id="branch-recovery",
        run_id="run-recovery",
        label="Recovery branch",
        status=BranchStatus.BLOCKED,
        current_stage_key=StageKey.VERIFY,
        stages=[verify_stage],
        score=BranchScore(
            exploration_priority=0.5,
            result_quality=0.9,
            rationale="Recovery branch needs verification before it can advance.",
        ),
        lineage=BranchLineage(source_summary="Created in recovery test state."),
        artifact_ids=["artifact-verify"],
    )
    artifact = _artifact(
        "artifact-verify",
        branch.branch_id,
        StageKey.VERIFY,
        kind=ArtifactKind.RESULT,
        reuse_level=ArtifactReuseLevel.REPLAY_REQUIRED,
    )

    from v3.contracts.run import RunBoardSnapshot, RunStatus

    state_store.write_branch_snapshot(branch)
    state_store.write_stage_snapshot(branch.branch_id, verify_stage)
    state_store.write_artifact_snapshot(artifact)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-recovery",
            title="Recovery board",
            scenario_label="data_science",
            status=RunStatus.ACTIVE,
            primary_branch_id=branch.branch_id,
            branch_ids=[branch.branch_id],
            highlighted_artifact_ids=[artifact.artifact_id],
            summary="Recovery summary.",
        )
    )
    return artifact


def _seed_selection_state(state_store: ArtifactStateStore) -> tuple[BranchSnapshot, BranchSnapshot]:
    framing_stage = StageSnapshot(
        stage_key=StageKey.FRAMING,
        status=StageStatus.COMPLETED,
        summary="Framing completed.",
        artifact_ids=["artifact-framing-a"],
        next_stage_key=StageKey.BUILD,
    )
    build_stage = StageSnapshot(
        stage_key=StageKey.BUILD,
        status=StageStatus.COMPLETED,
        summary="Build completed.",
        artifact_ids=["artifact-build-b"],
        next_stage_key=StageKey.VERIFY,
    )

    branch_a = BranchSnapshot(
        branch_id="branch-select-a",
        run_id="run-select",
        label="Select A",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.FRAMING,
        stages=[framing_stage],
        score=BranchScore(
            exploration_priority=0.85,
            result_quality=0.62,
            rationale="High exploration potential.",
        ),
        lineage=BranchLineage(source_summary="Selection seed A."),
        artifact_ids=["artifact-framing-a"],
    )
    branch_b = BranchSnapshot(
        branch_id="branch-select-b",
        run_id="run-select",
        label="Select B",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.BUILD,
        stages=[build_stage],
        score=BranchScore(
            exploration_priority=0.41,
            result_quality=0.92,
            rationale="Strong verified results.",
        ),
        lineage=BranchLineage(source_summary="Selection seed B."),
        artifact_ids=["artifact-build-b"],
    )

    state_store.write_branch_snapshot(branch_a)
    state_store.write_branch_snapshot(branch_b)
    state_store.write_stage_snapshot(branch_a.branch_id, framing_stage)
    state_store.write_stage_snapshot(branch_b.branch_id, build_stage)
    state_store.write_artifact_snapshot(_artifact("artifact-framing-a", branch_a.branch_id, StageKey.FRAMING))
    state_store.write_artifact_snapshot(_artifact("artifact-build-b", branch_b.branch_id, StageKey.BUILD))
    state_store.write_run_snapshot(
        __import__("v3.contracts.run", fromlist=["RunBoardSnapshot", "RunStatus"]).RunBoardSnapshot(
            run_id="run-select",
            title="Selection board",
            scenario_label="data_science",
            status=__import__("v3.contracts.run", fromlist=["RunStatus"]).RunStatus.ACTIVE,
            primary_branch_id=branch_a.branch_id,
            branch_ids=[branch_a.branch_id, branch_b.branch_id],
            highlighted_artifact_ids=["artifact-build-b"],
            summary="Selection summary.",
        )
    )
    state_store.write_recovery_assessment(
        RecoveryAssessment(
            run_id="run-select",
            branch_id=branch_a.branch_id,
            stage_key=StageKey.FRAMING,
            recovery_assessment=RecoveryDisposition.REPLAY,
            reusable_artifact_ids=[],
            replay_artifact_ids=["artifact-framing-a"],
            invalid_reasons=[],
            recommended_next_step="replay framing evidence before advancing to build",
        )
    )
    state_store.write_recovery_assessment(
        RecoveryAssessment(
            run_id="run-select",
            branch_id=branch_b.branch_id,
            stage_key=StageKey.BUILD,
            recovery_assessment=RecoveryDisposition.REUSE,
            reusable_artifact_ids=["artifact-build-b"],
            replay_artifact_ids=[],
            invalid_reasons=[],
            recommended_next_step="continue with verify",
        )
    )
    return branch_a, branch_b


def test_rd_run_start_creates_v3_run_truth_and_uses_execution_port(tmp_path: Path) -> None:
    from v3.orchestration.run_board_service import RunBoardService
    from v3.tools.run_tools import rd_run_start

    state_store = ArtifactStateStore(tmp_path / "state")
    execution_port = SpyExecutionPort()
    service = RunBoardService(state_store=state_store, execution_port=execution_port)
    request = RunStartRequest(
        title="Boundary reset",
        task_summary="Publish the initial V3 run truth.",
        scenario_label="data_science",
        initial_branch_label="Primary branch",
    )

    result = rd_run_start(request, service=service)

    assert execution_port.requests == [request]
    assert state_store.load_run_snapshot("run-start") is not None
    assert state_store.load_branch_snapshot("branch-start") is not None
    assert state_store.load_stage_snapshot("branch-start", StageKey.FRAMING) is not None
    assert state_store.list_artifact_snapshots("run-start", branch_id="branch-start", stage_key=StageKey.FRAMING)
    assert result["structuredContent"]["run"]["run_id"] == "run-start"
    assert result["structuredContent"]["branch"]["branch_id"] == "branch-start"
    assert result["structuredContent"]["stage"]["stage_key"] == "framing"
    assert result["content"][0]["type"] == "text"
    assert "run-start" in result["content"][0]["text"]
    assert "app.control_plane" not in sys.modules
    assert "app.runtime" not in sys.modules


def test_rd_run_branch_and_stage_handlers_read_canonical_v3_snapshots_with_text_fallback(tmp_path: Path) -> None:
    from v3.orchestration.run_board_service import RunBoardService
    from v3.tools.branch_tools import rd_branch_get, rd_branch_list
    from v3.tools.run_tools import rd_run_get
    from v3.tools.stage_tools import rd_stage_get

    state_store = ArtifactStateStore(tmp_path / "state")
    primary_branch, completed_branch, framing_artifact, _ = _seed_run_state(state_store)
    run_service = RunBoardService(state_store=state_store)

    run_result = rd_run_get(RunGetRequest(run_id="run-001"), service=run_service)
    branch_result = rd_branch_get(BranchGetRequest(branch_id=primary_branch.branch_id), state_store=state_store)
    active_only = rd_branch_list(
        BranchListRequest(run_id="run-001", include_completed=False),
        state_store=state_store,
    )
    stage_result = rd_stage_get(
        StageGetRequest(branch_id=primary_branch.branch_id, stage_key=StageKey.FRAMING),
        state_store=state_store,
    )

    assert run_result["structuredContent"]["run"]["run_id"] == "run-001"
    assert branch_result["structuredContent"]["branch"]["branch_id"] == primary_branch.branch_id
    assert [item["branch_id"] for item in active_only["structuredContent"]["items"]] == [primary_branch.branch_id]
    assert completed_branch.branch_id not in active_only["content"][0]["text"]
    assert stage_result["structuredContent"]["stage"]["stage_key"] == "framing"
    assert stage_result["structuredContent"]["items"] == [framing_artifact.model_dump(mode="json")]
    assert "framing" in stage_result["content"][0]["text"]


def test_rd_artifact_list_reads_canonical_v3_artifact_metadata(tmp_path: Path) -> None:
    from v3.tools.artifact_tools import rd_artifact_list

    state_store = ArtifactStateStore(tmp_path / "state")
    primary_branch, _, framing_artifact, _ = _seed_run_state(state_store)
    stray_path = tmp_path / "workspace" / "artifact-framing.json"
    stray_path.parent.mkdir(parents=True, exist_ok=True)
    stray_path.write_text('{"artifact_id": "workspace-only"}\n')

    result = rd_artifact_list(
        ArtifactListRequest(
            run_id="run-001",
            branch_id=primary_branch.branch_id,
            stage_key=StageKey.FRAMING,
        ),
        state_store=state_store,
    )

    assert result["structuredContent"]["run_id"] == "run-001"
    assert result["structuredContent"]["branch_id"] == primary_branch.branch_id
    assert result["structuredContent"]["items"] == [framing_artifact.model_dump(mode="json")]
    assert "workspace-only" not in result["content"][0]["text"]


def test_rd_recovery_assess_returns_structured_v3_recovery_content_with_text_fallback(tmp_path: Path) -> None:
    from v3.orchestration.recovery_service import RecoveryService
    from v3.tools.recovery_tools import rd_recovery_assess

    state_store = ArtifactStateStore(tmp_path / "state")
    artifact = _seed_recovery_state(state_store)
    service = RecoveryService(state_store)

    result = rd_recovery_assess(
        RecoveryAssessRequest(
            run_id="run-recovery",
            branch_id="branch-recovery",
            stage_key=StageKey.VERIFY,
        ),
        service=service,
    )

    assert result["structuredContent"]["assessment"]["branch_id"] == "branch-recovery"
    assert result["structuredContent"]["assessment"]["recovery_assessment"] == RecoveryDisposition.REPLAY.value
    assert result["structuredContent"]["assessment"]["replay_artifact_ids"] == [artifact.artifact_id]
    assert [reason["code"] for reason in result["structuredContent"]["assessment"]["invalid_reasons"]] == [
        RecoveryReasonCode.STAGE_BLOCKED.value,
        RecoveryReasonCode.ARTIFACTS_STALE.value,
    ]
    assert "replay verify evidence" in result["content"][0]["text"]


def test_rd_branch_select_next_returns_v3_recommendation_without_scheduler_leakage(tmp_path: Path) -> None:
    from v3.tools.selection_tools import BranchSelectNextRequest, rd_branch_select_next

    state_store = ArtifactStateStore(tmp_path / "state")
    _, selected_branch = _seed_selection_state(state_store)

    result = rd_branch_select_next(
        BranchSelectNextRequest(run_id="run-select"),
        state_store=state_store,
    )

    recommendation = result["structuredContent"]["recommendation"]
    assert recommendation["branch_id"] == selected_branch.branch_id
    assert recommendation["exploration_priority"] >= 0.0
    assert recommendation["result_quality"] >= 0.0
    assert recommendation["current_stage_key"] == selected_branch.current_stage_key.value
    assert recommendation["recommended_next_step"] == "continue with verify"
    assert "scheduler" not in result["content"][0]["text"].lower()
    assert "head_node_id" not in str(result["structuredContent"])


def test_phase13_minimal_tool_subset_remains_present_in_phase16_registry() -> None:
    from v3.entry.tool_catalog import list_cli_tools

    tools = {tool["name"] for tool in list_cli_tools()}

    assert {
        "rd_run_start",
        "rd_run_get",
        "rd_branch_get",
        "rd_branch_list",
        "rd_stage_get",
        "rd_artifact_list",
        "rd_recovery_assess",
        "rd_branch_select_next",
        "rd_memory_create",
        "rd_memory_get",
        "rd_memory_list",
        "rd_memory_promote",
        "rd_branch_paths_get",
    }.issubset(tools)


def test_phase13_registry_schemas_derive_from_phase13_pydantic_contracts() -> None:
    from v3.entry.tool_catalog import list_cli_tools

    tools = {tool["name"]: tool for tool in list_cli_tools()}

    assert tools["rd_run_start"]["inputSchema"] == RunStartRequest.model_json_schema()
    assert tools["rd_run_get"]["inputSchema"] == RunGetRequest.model_json_schema()
    assert tools["rd_run_get"]["outputSchema"] == RunGetResult.model_json_schema()
    assert tools["rd_branch_get"]["inputSchema"] == BranchGetRequest.model_json_schema()
    assert tools["rd_branch_get"]["outputSchema"] == BranchGetResult.model_json_schema()
    assert tools["rd_branch_list"]["inputSchema"] == BranchListRequest.model_json_schema()
    assert tools["rd_branch_list"]["outputSchema"] == BranchListResult.model_json_schema()
    assert tools["rd_stage_get"]["inputSchema"] == StageGetRequest.model_json_schema()
    assert tools["rd_stage_get"]["outputSchema"] == StageGetResult.model_json_schema()
    assert tools["rd_artifact_list"]["inputSchema"] == ArtifactListRequest.model_json_schema()
    assert tools["rd_artifact_list"]["outputSchema"] == ArtifactListResult.model_json_schema()
    assert tools["rd_recovery_assess"]["inputSchema"] == RecoveryAssessRequest.model_json_schema()
    assert tools["rd_recovery_assess"]["outputSchema"] == RecoveryAssessResult.model_json_schema()
    assert tools["rd_branch_select_next"]["inputSchema"]["title"] == "BranchSelectNextRequest"
    assert tools["rd_branch_select_next"]["outputSchema"]["title"] == "BranchSelectNextResult"
    assert tools["rd_memory_create"]["inputSchema"] == MemoryCreateRequest.model_json_schema()
    assert tools["rd_memory_create"]["outputSchema"] == MemoryGetResult.model_json_schema()
    assert tools["rd_memory_get"]["inputSchema"] == MemoryGetRequest.model_json_schema()
    assert tools["rd_memory_get"]["outputSchema"] == MemoryGetResult.model_json_schema()
    assert tools["rd_memory_list"]["inputSchema"] == MemoryListRequest.model_json_schema()
    assert tools["rd_memory_list"]["outputSchema"] == MemoryListResult.model_json_schema()
    assert tools["rd_memory_promote"]["inputSchema"] == MemoryPromoteRequest.model_json_schema()
    assert tools["rd_memory_promote"]["outputSchema"] == MemoryGetResult.model_json_schema()
    assert tools["rd_branch_paths_get"]["inputSchema"] == BranchPathsGetRequest.model_json_schema()
    assert tools["rd_branch_paths_get"]["outputSchema"] == BranchPathsGetResult.model_json_schema()


def test_tool_structured_content_matches_advertised_response_models(tmp_path: Path) -> None:
    from v3.entry.tool_catalog import RunStartToolResult
    from v3.orchestration.branch_isolation_service import BranchIsolationService
    from v3.orchestration.memory_service import MemoryService
    from v3.orchestration.memory_state_store import MemoryStateStore
    from v3.orchestration.recovery_service import RecoveryService
    from v3.orchestration.run_board_service import RunBoardService
    from v3.tools.artifact_tools import rd_artifact_list
    from v3.tools.branch_tools import rd_branch_get, rd_branch_list
    from v3.tools.isolation_tools import rd_branch_paths_get
    from v3.tools.memory_tools import rd_memory_create, rd_memory_get, rd_memory_list, rd_memory_promote
    from v3.tools.recovery_tools import rd_recovery_assess
    from v3.tools.run_tools import rd_run_get, rd_run_start
    from v3.tools.selection_tools import BranchSelectNextRequest, BranchSelectNextResult, rd_branch_select_next
    from v3.tools.stage_tools import rd_stage_get

    state_store = ArtifactStateStore(tmp_path / "state")
    execution_port = SpyExecutionPort()
    run_service = RunBoardService(state_store=state_store, execution_port=execution_port)
    start_request = RunStartRequest(
        title="Conformance run",
        task_summary="Validate registry and handler output conformance.",
        scenario_label="data_science",
        initial_branch_label="Primary branch",
    )
    run_start_result = rd_run_start(start_request, service=run_service)
    RunStartToolResult.model_validate(run_start_result["structuredContent"])

    primary_branch, _, framing_artifact, _ = _seed_run_state(state_store)
    run_get_result = rd_run_get(RunGetRequest(run_id="run-001"), service=RunBoardService(state_store=state_store))
    branch_get_result = rd_branch_get(BranchGetRequest(branch_id=primary_branch.branch_id), state_store=state_store)
    branch_list_result = rd_branch_list(BranchListRequest(run_id="run-001"), state_store=state_store)
    stage_get_result = rd_stage_get(
        StageGetRequest(branch_id=primary_branch.branch_id, stage_key=StageKey.FRAMING),
        state_store=state_store,
    )
    artifact_list_result = rd_artifact_list(
        ArtifactListRequest(run_id="run-001", branch_id=primary_branch.branch_id, stage_key=StageKey.FRAMING),
        state_store=state_store,
    )

    RunGetResult.model_validate(run_get_result["structuredContent"])
    BranchGetResult.model_validate(branch_get_result["structuredContent"])
    BranchListResult.model_validate(branch_list_result["structuredContent"])
    StageGetResult.model_validate(stage_get_result["structuredContent"])
    ArtifactListResult.model_validate(artifact_list_result["structuredContent"])

    _seed_recovery_state(state_store)
    recovery_result = rd_recovery_assess(
        RecoveryAssessRequest(
            run_id="run-recovery",
            branch_id="branch-recovery",
            stage_key=StageKey.VERIFY,
        ),
        service=RecoveryService(state_store),
    )
    RecoveryAssessResult.model_validate(recovery_result["structuredContent"])

    _seed_selection_state(state_store)
    selection_result = rd_branch_select_next(
        BranchSelectNextRequest(run_id="run-select"),
        state_store=state_store,
    )
    BranchSelectNextResult.model_validate(selection_result["structuredContent"])

    memory_service = MemoryService(MemoryStateStore(tmp_path / "memory-state"))
    memory_create_result = rd_memory_create(
        MemoryCreateRequest(
            memory_id="memory-001",
            run_id="run-001",
            branch_id=primary_branch.branch_id,
            stage_key=StageKey.VERIFY,
            hypothesis="Validate registry memory surface.",
            score=0.93,
            reason="Structured content must match advertised schemas.",
            evidence=["artifact-build"],
            outcome="passed",
            tags=["verify"],
        ),
        service=memory_service,
    )
    memory_get_result = rd_memory_get(
        MemoryGetRequest(memory_id="memory-001", run_id="run-001", owner_branch_id=primary_branch.branch_id),
        service=memory_service,
    )
    memory_list_result = rd_memory_list(
        MemoryListRequest(
            run_id="run-001",
            branch_id=primary_branch.branch_id,
            stage_key=StageKey.VERIFY,
            task_query="registry memory surface",
            limit=5,
        ),
        service=memory_service,
    )
    memory_promote_result = rd_memory_promote(
        MemoryPromoteRequest(
            memory_id="memory-001",
            run_id="run-001",
            owner_branch_id=primary_branch.branch_id,
            promoted_by="reviewer-1",
            promotion_reason="Structured output verified.",
        ),
        service=memory_service,
    )
    branch_paths_result = rd_branch_paths_get(
        BranchPathsGetRequest(run_id="run-001", branch_id=primary_branch.branch_id),
        service=BranchIsolationService(tmp_path / "isolation-state"),
    )

    MemoryGetResult.model_validate(memory_create_result["structuredContent"])
    MemoryGetResult.model_validate(memory_get_result["structuredContent"])
    MemoryListResult.model_validate(memory_list_result["structuredContent"])
    MemoryGetResult.model_validate(memory_promote_result["structuredContent"])
    BranchPathsGetResult.model_validate(branch_paths_result["structuredContent"])

    assert stage_get_result["structuredContent"]["stage"]["stage_key"] == "framing"
    assert artifact_list_result["structuredContent"]["items"][0]["artifact_id"] == framing_artifact.artifact_id
    assert memory_list_result["structuredContent"]["items"][0]["memory_id"] == "memory-001"
    assert memory_promote_result["structuredContent"]["shared_namespace"] == "shared"
    assert branch_paths_result["structuredContent"]["paths"]["branch_id"] == primary_branch.branch_id


def test_registry_surface_stays_free_of_legacy_dto_names() -> None:
    from v3.entry.tool_catalog import list_cli_tools

    registry_text = str(list_cli_tools())

    assert "RunSession" not in registry_text
    assert "head_node_id" not in registry_text
    assert "app.runtime" not in registry_text
    assert "app.query_services" not in registry_text


def test_v3_tools_package_exports_phase15_public_handlers() -> None:
    from v3 import tools as exported_tools

    assert exported_tools.rd_memory_create is not None
    assert exported_tools.rd_memory_get is not None
    assert exported_tools.rd_memory_list is not None
    assert exported_tools.rd_memory_promote is not None
    assert exported_tools.rd_branch_paths_get is not None


def test_importlinter_forbids_v3_tool_layer_fallbacks() -> None:
    config_text = (ROOT / ".importlinter").read_text(encoding="utf-8")

    assert "[importlinter:v3_tools_are_isolated_from_legacy_runtime]" in config_text
    assert "source_modules =" in config_text
    assert "v3.tools" in config_text
    assert "forbidden_modules =" in config_text
    assert "service_contracts" in config_text
    assert "data_models" in config_text
    assert "exploration_manager" in config_text
    assert "app.query_services" in config_text
    assert "app.runtime" in config_text
    assert "core.loop" in config_text


@pytest.mark.parametrize(
    "relative_path",
    [
        "v3/tools/run_tools.py",
        "v3/tools/branch_tools.py",
        "v3/tools/stage_tools.py",
        "v3/tools/artifact_tools.py",
        "v3/tools/recovery_tools.py",
        "v3/tools/selection_tools.py",
        "v3/tools/memory_tools.py",
        "v3/tools/isolation_tools.py",
        "v3/entry/tool_catalog.py",
    ],
)
def test_phase13_task1_tool_modules_do_not_import_legacy_runtime_surfaces(relative_path: str) -> None:
    imports = _import_names(ROOT / relative_path)
    violations = sorted(
        name
        for name in imports
        if any(name == forbidden or name.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_IMPORTS)
    )

    assert not violations, f"Forbidden imports in {relative_path}: {violations}"
