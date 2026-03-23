from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from v3.contracts.artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.memory import MemoryKind, MemoryNamespace, MemoryPromotionSnapshot, MemoryRecordSnapshot
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import BranchPathsGetRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_isolation_service import BranchIsolationService
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.memory_state_store import MemoryStateStore
from v3.tools.isolation_tools import rd_branch_paths_get


def test_branch_isolation_service_returns_branch_scoped_paths(tmp_path: Path) -> None:
    service = BranchIsolationService(tmp_path / "state")

    snapshot = service.snapshot(run_id="run-001", branch_id="branch-001")

    assert snapshot.run_id == "run-001"
    assert snapshot.branch_id == "branch-001"
    assert snapshot.branch_root == str(tmp_path / "state" / "branches" / "branch-001")
    assert snapshot.artifact_root == str(tmp_path / "state" / "artifacts" / "run-001" / "branch-001")
    assert snapshot.memory_root == str(tmp_path / "state" / "memory" / "run-001" / "branches" / "branch-001")
    assert snapshot.shared_memory_root == str(tmp_path / "state" / "memory" / "run-001" / "shared")
    assert snapshot.workspace_root == str(
        tmp_path / "state" / "workspaces" / "run-001" / "branches" / "branch-001" / "workspace"
    )

    assert "workspaces/run-001/branches/branch-001/workspace" in snapshot.workspace_root


def test_branch_workspace_manager_allocates_canonical_branch_workspace(tmp_path: Path) -> None:
    manager = BranchWorkspaceManager(tmp_path / "state")

    workspace_root = Path(manager.allocate_branch_workspace(run_id="run-001", branch_id="branch-001"))

    assert workspace_root == (tmp_path / "state" / "workspaces" / "run-001" / "branches" / "branch-001" / "workspace")
    assert workspace_root.exists()
    assert workspace_root.is_dir()


def test_branch_isolated_layout_keeps_shared_memory_outside_local_branch_root(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    artifact_store = ArtifactStateStore(state_root)
    memory_store = MemoryStateStore(state_root)
    isolation_service = BranchIsolationService(state_root)

    stage = StageSnapshot(
        stage_key=StageKey.FRAMING,
        status=StageStatus.IN_PROGRESS,
        summary="Framing is underway.",
        artifact_ids=["artifact-001"],
        next_stage_key=StageKey.BUILD,
    )
    branch = BranchSnapshot(
        branch_id="branch-001",
        run_id="run-001",
        label="Primary branch",
        status=BranchStatus.ACTIVE,
        current_stage_key=stage.stage_key,
        stages=[stage],
        score=BranchScore(
            exploration_priority=0.9,
            result_quality=0.4,
            rationale="Primary branch owns the current work.",
        ),
        lineage=BranchLineage(source_summary="Created for branch isolation verification."),
        artifact_ids=["artifact-001"],
    )
    artifact_store.write_branch_snapshot(branch)
    artifact_receipt = artifact_store.write_artifact_snapshot(
        ArtifactSnapshot(
            artifact_id="artifact-001",
            branch_id="branch-001",
            stage_key=StageKey.FRAMING,
            kind=ArtifactKind.PLAN,
            title="Plan artifact",
            summary="Canonical branch artifact.",
            locator=ArtifactLocator(
                uri="memory://artifacts/artifact-001.md",
                media_type="text/markdown",
                size_bytes=128,
            ),
            provenance=ArtifactProvenance(
                created_by="planner",
                derived_from_artifact_ids=[],
                source_branch_ids=["branch-001"],
                captured_at="2026-03-20T11:50:00Z",
            ),
            reuse_level=ArtifactReuseLevel.REUSABLE,
            tags=["plan"],
        )
    )

    record = MemoryRecordSnapshot(
        memory_id="memory-001",
        run_id="run-001",
        owner_branch_id="branch-001",
        stage_key=StageKey.FRAMING,
        kind=MemoryKind.ATOMIC,
        hypothesis="Branch-local memory",
        score=0.88,
        reason="Useful branch-local note",
        evidence=["artifact-001"],
        outcome="stable",
        tags=["framing"],
    )
    promotion = MemoryPromotionSnapshot(
        memory_id="memory-001",
        run_id="run-001",
        owner_branch_id="branch-001",
        promotion_reason="Stable enough to share",
        promoted_by="reviewer-1",
        promoted_at=datetime.now(UTC).isoformat(),
        shared_namespace=MemoryNamespace.SHARED,
    )
    memory_receipt = memory_store.write_memory_record(record)
    promotion_receipt = memory_store.write_memory_promotion(promotion)

    branch_paths = rd_branch_paths_get(
        BranchPathsGetRequest(run_id="run-001", branch_id="branch-001"),
        service=isolation_service,
    )

    expected_artifact_root = state_root / "artifacts" / "run-001" / "branch-001"
    expected_memory_root = state_root / "memory" / "run-001" / "branches" / "branch-001"
    expected_shared_root = state_root / "memory" / "run-001" / "shared"
    expected_workspace_root = state_root / "workspaces" / "run-001" / "branches" / "branch-001" / "workspace"

    assert artifact_receipt.storage_uri == str(expected_artifact_root / "framing" / "artifact-001.json")
    assert memory_receipt.storage_uri == str(expected_memory_root / "records" / "memory-001.json")
    assert promotion_receipt.storage_uri == str(expected_shared_root / "promotions" / "memory-001.json")
    assert expected_shared_root.parent != expected_memory_root
    assert "memory/run-001/branches/branch-001" in memory_receipt.storage_uri

    structured = branch_paths["structuredContent"]
    assert structured["paths"]["artifact_root"] == str(expected_artifact_root)
    assert structured["paths"]["memory_root"] == str(expected_memory_root)
    assert structured["paths"]["shared_memory_root"] == str(expected_shared_root)
    assert structured["paths"]["workspace_root"] == str(expected_workspace_root)
    assert "workspace_root" in branch_paths["content"][0]["text"]
    assert "memory_root" in branch_paths["content"][0]["text"]
    assert "shared_memory_root" in branch_paths["content"][0]["text"]
    assert "checkpoint" not in branch_paths["content"][0]["text"].lower()
    assert "node" not in branch_paths["content"][0]["text"].lower()
