from __future__ import annotations

from pathlib import Path

import pytest

from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import BranchDecisionKind, BranchResolution
from v3.contracts.recovery import RecoveryAssessment, RecoveryDisposition
from v3.contracts.run import RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import BranchPruneRequest, BranchSelectNextRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore


def _branch(
    branch_id: str,
    *,
    exploration_priority: float,
    result_quality: float,
    current_stage_key: StageKey,
) -> BranchSnapshot:
    stage = StageSnapshot(
        stage_key=current_stage_key,
        status=StageStatus.COMPLETED,
        summary=f"{branch_id} completed {current_stage_key.value}.",
        next_stage_key=StageKey.VERIFY if current_stage_key is StageKey.BUILD else StageKey.BUILD,
    )
    return BranchSnapshot(
        branch_id=branch_id,
        run_id="run-select",
        label=f"{branch_id} label",
        status=BranchStatus.ACTIVE,
        current_stage_key=current_stage_key,
        stages=[stage],
        score=BranchScore(
            exploration_priority=exploration_priority,
            result_quality=result_quality,
            rationale=f"{branch_id} public score.",
        ),
        lineage=BranchLineage(source_summary=f"Seeded for {branch_id}."),
        artifact_ids=[],
    )


def _recovery(
    branch_id: str,
    *,
    stage_key: StageKey,
    recovery_assessment: RecoveryDisposition,
    next_step: str,
) -> RecoveryAssessment:
    return RecoveryAssessment(
        run_id="run-select",
        branch_id=branch_id,
        stage_key=stage_key,
        recovery_assessment=recovery_assessment,
        reusable_artifact_ids=["artifact"] if recovery_assessment is RecoveryDisposition.REUSE else [],
        replay_artifact_ids=["artifact"] if recovery_assessment is not RecoveryDisposition.REUSE else [],
        invalid_reasons=[],
        recommended_next_step=next_step,
    )


def test_rd_branch_select_next_uses_v3_puct_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from v3.tools.selection_tools import rd_branch_select_next

    state_store = ArtifactStateStore(tmp_path / "state")
    branch_a = _branch(
        "branch-select-a",
        exploration_priority=0.85,
        result_quality=0.62,
        current_stage_key=StageKey.FRAMING,
    )
    branch_b = _branch(
        "branch-select-b",
        exploration_priority=0.41,
        result_quality=0.92,
        current_stage_key=StageKey.BUILD,
    )
    state_store.write_branch_snapshot(branch_a)
    state_store.write_branch_snapshot(branch_b)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-select",
            title="Selection board",
            status=RunStatus.ACTIVE,
            branch_ids=[branch_a.branch_id, branch_b.branch_id],
            primary_branch_id=branch_a.branch_id,
            highlighted_artifact_ids=[],
            summary="Selection summary.",
        )
    )
    state_store.write_recovery_assessment(
        _recovery(
            branch_a.branch_id,
            stage_key=StageKey.FRAMING,
            recovery_assessment=RecoveryDisposition.REPLAY,
            next_step="replay framing evidence before advancing to build",
        )
    )
    state_store.write_recovery_assessment(
        _recovery(
            branch_b.branch_id,
            stage_key=StageKey.BUILD,
            recovery_assessment=RecoveryDisposition.REUSE,
            next_step="continue with verify",
        )
    )

    seen: dict[str, list[str]] = {}

    def _fake_select_next_branch(self, candidates):
        seen["branch_ids"] = [candidate.branch_id for candidate in candidates]
        return branch_b.branch_id

    monkeypatch.setattr(
        "v3.orchestration.selection_service.PuctSelectionAdapter.select_next_branch",
        _fake_select_next_branch,
    )

    result = rd_branch_select_next(BranchSelectNextRequest(run_id="run-select"), state_store=state_store)
    decisions = state_store.list_branch_decisions("run-select", branch_id=branch_b.branch_id)
    run = state_store.load_run_snapshot("run-select")

    assert seen["branch_ids"] == [branch_a.branch_id, branch_b.branch_id]
    assert result["structuredContent"]["recommendation"]["branch_id"] == branch_b.branch_id
    assert "v3 puct adapter" in result["structuredContent"]["recommendation"]["rationale"].lower()
    assert result["content"][0]["text"].startswith("Recommended branch")
    assert decisions[-1].kind is BranchDecisionKind.SELECT
    assert run is not None
    assert run.latest_branch_decision_id == decisions[-1].decision_id


def test_prune_policy_keeps_at_least_one_active_branch() -> None:
    from v3.orchestration.branch_board_service import BranchBoardService
    from v3.orchestration.branch_prune_service import BranchPruneService
    from v3.tools.exploration_tools import rd_branch_prune

    state_store = ArtifactStateStore(Path.cwd() / ".tmp-phase16-prune-state")
    branches = [
        _branch("branch-prune-a", exploration_priority=0.6, result_quality=0.92, current_stage_key=StageKey.BUILD),
        _branch("branch-prune-b", exploration_priority=0.45, result_quality=0.42, current_stage_key=StageKey.BUILD),
    ]
    for branch in branches:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-select",
            title="Prune board",
            status=RunStatus.ACTIVE,
            branch_ids=[branch.branch_id for branch in branches],
            primary_branch_id=branches[0].branch_id,
            highlighted_artifact_ids=[],
            summary="Prune summary.",
        )
    )
    service = BranchPruneService(state_store=state_store, board_service=BranchBoardService(state_store))

    result = rd_branch_prune(
        BranchPruneRequest(run_id="run-select", relative_threshold=0.6),
        service=service,
    )

    pruned_branch = state_store.load_branch_snapshot("branch-prune-b")
    active_branch = state_store.load_branch_snapshot("branch-prune-a")
    decisions = state_store.list_branch_decisions("run-select", branch_id="branch-prune-b")

    assert result["structuredContent"]["pruned_branch_ids"] == ["branch-prune-b"]
    assert result["structuredContent"]["active_branch_ids"] == ["branch-prune-a"]
    assert pruned_branch is not None
    assert pruned_branch.status is BranchStatus.SUPERSEDED
    assert pruned_branch.resolution is BranchResolution.PRUNED
    assert active_branch is not None
    assert active_branch.status is BranchStatus.ACTIVE
    assert decisions[-1].kind is BranchDecisionKind.PRUNE
