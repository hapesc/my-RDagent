from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

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

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_preflight_symbols() -> tuple[Any, Any]:
    contracts = importlib.import_module("rd_agent.contracts.preflight")
    service_module = importlib.import_module("rd_agent.orchestration.preflight_service")
    return contracts.PreflightBlockerCategory, service_module.PreflightService


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


def _seed_state(
    tmp_path: Path,
    *,
    run_id: str = "run-001",
    branch_id: str = "branch-001",
    stage_key: StageKey = StageKey.BUILD,
    branch_current_stage_key: StageKey | None = None,
    stage_status: StageStatus = StageStatus.READY,
    stage_iteration: int = 1,
    artifact_ids: list[str] | None = None,
    write_artifacts: bool = True,
    write_recovery: bool = False,
    artifact_reuse_level: ArtifactReuseLevel = ArtifactReuseLevel.REUSABLE,
) -> ArtifactStateStore:
    state_store = ArtifactStateStore(tmp_path / "state")
    artifact_ids = ["build-artifact-001"] if artifact_ids is None else artifact_ids
    branch_current_stage_key = stage_key if branch_current_stage_key is None else branch_current_stage_key
    stage = StageSnapshot(
        stage_key=stage_key,
        stage_iteration=stage_iteration,
        status=stage_status,
        summary=f"{stage_key.value} summary",
        artifact_ids=list(artifact_ids),
        next_stage_key=StageKey.VERIFY if stage_key is StageKey.BUILD else StageKey.SYNTHESIZE,
    )
    branch = BranchSnapshot(
        branch_id=branch_id,
        run_id=run_id,
        label="Primary branch",
        status=BranchStatus.ACTIVE,
        current_stage_key=branch_current_stage_key,
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
        run_id=run_id,
        title="Phase 23",
        scenario_label="research",
        status=RunStatus.ACTIVE,
        execution_mode=ExecutionMode.UNATTENDED,
        max_stage_iterations=3,
        primary_branch_id=branch_id,
        branch_ids=[branch_id],
        highlighted_artifact_ids=list(artifact_ids),
        summary="Active run board.",
    )
    state_store.write_run_snapshot(run)
    state_store.write_branch_snapshot(branch)
    state_store.write_stage_snapshot(branch_id, stage)
    if write_artifacts:
        for artifact_id in artifact_ids:
            state_store.write_artifact_snapshot(
                _artifact(
                    artifact_id,
                    branch_id,
                    stage_key,
                    reuse_level=artifact_reuse_level,
                )
            )
    if write_recovery:
        assessment = RecoveryService(state_store).assess(branch_id, stage_key)
        if assessment is None:
            raise AssertionError("expected recovery assessment to persist")
    return state_store


def _make_service(
    state_store: ArtifactStateStore,
    *,
    python_version: tuple[int, int, int] = (3, 11, 0),
    command_exists: dict[str, bool] | None = None,
    module_exists: dict[str, bool] | None = None,
) -> Any:
    _, preflight_service_cls = _load_preflight_symbols()
    command_exists = {"uv": True} if command_exists is None else command_exists
    module_exists = (
        {"pydantic": True, "pytest": True, "import_linter": True} if module_exists is None else module_exists
    )
    return preflight_service_cls(
        state_store,
        project_root=REPO_ROOT,
        python_version_provider=lambda: python_version,
        command_exists_provider=lambda command: command_exists.get(command, False),
        module_exists_provider=lambda module_name: module_exists.get(module_name, False),
    )


def test_preflight_blocks_when_python_version_is_below_project_requirement(tmp_path: Path) -> None:
    categories, _ = _load_preflight_symbols()
    state_store = _seed_state(tmp_path)
    result = _make_service(state_store, python_version=(3, 10, 9)).assess(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=StageKey.BUILD,
        recommended_next_skill="rd-code",
    )

    assert result.readiness == "blocked"
    assert result.primary_blocker_category == categories.RUNTIME
    assert "3.11" in result.primary_blocker_reason
    assert "uv sync --extra test" in result.repair_action
    assert result.recommended_next_skill == "rd-code"


def test_preflight_blocks_when_uv_command_is_missing(tmp_path: Path) -> None:
    categories, _ = _load_preflight_symbols()
    state_store = _seed_state(tmp_path)
    result = _make_service(state_store, command_exists={"uv": False}).assess(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=StageKey.BUILD,
        recommended_next_skill="rd-code",
    )

    assert result.readiness == "blocked"
    assert result.primary_blocker_category == categories.RUNTIME
    assert "uv" in result.primary_blocker_reason
    assert "install uv" in result.repair_action.lower()
    assert result.recommended_next_skill == "rd-code"


def test_preflight_blocks_when_required_verify_dependencies_are_missing(tmp_path: Path) -> None:
    categories, _ = _load_preflight_symbols()
    state_store = _seed_state(tmp_path, stage_key=StageKey.VERIFY, artifact_ids=["verify-artifact-001"])
    result = _make_service(
        state_store,
        module_exists={"pydantic": True, "pytest": False, "import_linter": False},
    ).assess(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=StageKey.VERIFY,
        recommended_next_skill="rd-execute",
    )

    assert result.readiness == "blocked"
    assert result.primary_blocker_category == categories.DEPENDENCY
    assert "pytest" in result.primary_blocker_reason
    assert "import_linter" in result.primary_blocker_reason
    assert "uv sync --extra test" in result.repair_action
    assert result.recommended_next_skill == "rd-execute"


def test_preflight_blocks_when_stage_artifact_snapshot_is_missing(tmp_path: Path) -> None:
    categories, _ = _load_preflight_symbols()
    state_store = _seed_state(tmp_path, write_artifacts=False)
    result = _make_service(state_store).assess(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=StageKey.BUILD,
        recommended_next_skill="rd-code",
    )

    assert result.readiness == "blocked"
    assert result.primary_blocker_category == categories.ARTIFACT
    assert "build-artifact-001" in result.primary_blocker_reason
    assert "rebuild" in result.repair_action.lower()
    assert result.recommended_next_skill == "rd-code"


def test_preflight_blocks_when_branch_stage_disagrees_with_latest_snapshot(tmp_path: Path) -> None:
    categories, _ = _load_preflight_symbols()
    state_store = _seed_state(tmp_path, branch_current_stage_key=StageKey.VERIFY)
    result = _make_service(state_store).assess(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=StageKey.BUILD,
        recommended_next_skill="rd-code",
    )

    assert result.readiness == "blocked"
    assert result.primary_blocker_category == categories.STATE
    assert "current_stage_key" in result.primary_blocker_reason
    assert "repair persisted run/branch/stage snapshots" in result.repair_action.lower()
    assert result.recommended_next_skill == "rd-code"


def test_preflight_blocks_when_completed_stage_has_no_persisted_recovery_assessment(tmp_path: Path) -> None:
    categories, _ = _load_preflight_symbols()
    state_store = _seed_state(tmp_path, stage_status=StageStatus.COMPLETED)
    result = _make_service(state_store).assess(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=StageKey.BUILD,
        recommended_next_skill="rd-code",
    )

    assert result.readiness == "blocked"
    assert result.primary_blocker_category == categories.RECOVERY
    assert "recovery assessment" in result.primary_blocker_reason
    assert "persist a recovery assessment" in result.repair_action.lower()
    assert result.recommended_next_skill == "rd-code"


def test_preflight_passes_for_fresh_build_stage_when_runtime_and_state_truth_hold(tmp_path: Path) -> None:
    categories, _ = _load_preflight_symbols()
    state_store = _seed_state(tmp_path)
    result = _make_service(state_store).assess(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=StageKey.BUILD,
        recommended_next_skill="rd-code",
    )

    assert result.readiness == "executable"
    assert result.primary_blocker_category is None
    assert result.primary_blocker_reason is None
    assert result.repair_action == "None - canonical preflight truth passed."
    assert result.recommended_next_skill == "rd-code"
    assert result.blockers_by_category.runtime == []
    assert result.blockers_by_category.dependency == []
    assert result.blockers_by_category.artifact == []
    assert result.blockers_by_category.state == []
    assert result.blockers_by_category.recovery == []
    assert categories.RUNTIME.value == "runtime"
