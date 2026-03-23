from __future__ import annotations

from pathlib import Path

from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import BranchDecisionKind
from v3.contracts.memory import MemoryKind, MemoryNamespace
from v3.contracts.run import RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import (
    BranchShareApplyRequest,
    BranchShareAssessRequest,
    MemoryCreateRequest,
    MemoryListRequest,
)
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_share_service import BranchShareService
from v3.orchestration.memory_service import MemoryService
from v3.orchestration.memory_state_store import MemoryStateStore
from v3.tools.exploration_tools import rd_branch_share_apply, rd_branch_share_assess
from v3.tools.memory_tools import rd_memory_create


def _branch(branch_id: str, *, run_id: str = "run-share", quality: float = 0.82) -> BranchSnapshot:
    stage = StageSnapshot(
        stage_key=StageKey.BUILD,
        status=StageStatus.COMPLETED,
        summary=f"{branch_id} finished build.",
        next_stage_key=StageKey.VERIFY,
    )
    return BranchSnapshot(
        branch_id=branch_id,
        run_id=run_id,
        label=f"{branch_id} hypothesis",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.BUILD,
        stages=[stage],
        score=BranchScore(
            exploration_priority=0.7,
            result_quality=quality,
            rationale=f"{branch_id} score rationale.",
        ),
        lineage=BranchLineage(source_summary=f"Seeded for {branch_id}."),
        artifact_ids=[],
    )


def test_share_assess_combines_score_similarity_and_judge_signals(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    memory_service = MemoryService(MemoryStateStore(tmp_path / "memory"))
    share_service = BranchShareService(
        state_store=state_store,
        memory_service=memory_service,
        board_service=BranchBoardService(state_store),
    )
    source_branch = _branch("branch-source", quality=0.88)
    target_branch = _branch("branch-target", quality=0.73)
    for branch in [source_branch, target_branch]:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-share",
            title="Share board",
            status=RunStatus.ACTIVE,
            branch_ids=[source_branch.branch_id, target_branch.branch_id],
            primary_branch_id=source_branch.branch_id,
            highlighted_artifact_ids=[],
            summary="Share summary.",
        )
    )
    rd_memory_create(
        MemoryCreateRequest(
            memory_id="memory-share-source",
            run_id="run-share",
            branch_id=source_branch.branch_id,
            stage_key=StageKey.BUILD,
            hypothesis="Promote the validated build insight",
            score=0.94,
            reason="Strong build evidence",
            kind=MemoryKind.ATOMIC,
            evidence=["benchmark trace"],
            outcome="passed",
            tags=["build", "insight"],
        ),
        service=memory_service,
    )

    result = rd_branch_share_assess(
        BranchShareAssessRequest(
            run_id="run-share",
            source_branch_id=source_branch.branch_id,
            target_branch_id=target_branch.branch_id,
            similarity=0.82,
            judge_allows_share=True,
        ),
        service=share_service,
    )
    decisions = state_store.list_branch_decisions("run-share", branch_id=target_branch.branch_id)

    assert result["structuredContent"]["eligible"] is True
    assert result["structuredContent"]["granularity"] == "record"
    assert "score=0.88" in result["structuredContent"]["rationale"]
    assert "similarity=0.82" in result["structuredContent"]["rationale"]
    assert decisions[-1].kind is BranchDecisionKind.SHARE
    assert decisions[-1].source_branch_id == source_branch.branch_id


def test_share_apply_promotes_branch_knowledge_with_provenance_and_run_sync(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    memory_service = MemoryService(MemoryStateStore(tmp_path / "memory"))
    share_service = BranchShareService(
        state_store=state_store,
        memory_service=memory_service,
        board_service=BranchBoardService(state_store),
    )
    source_branch = _branch("branch-source", quality=0.91)
    target_branch = _branch("branch-target", quality=0.75)
    for branch in [source_branch, target_branch]:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-share",
            title="Share board",
            status=RunStatus.ACTIVE,
            branch_ids=[source_branch.branch_id, target_branch.branch_id],
            primary_branch_id=source_branch.branch_id,
            highlighted_artifact_ids=[],
            summary="Share summary.",
        )
    )
    rd_memory_create(
        MemoryCreateRequest(
            memory_id="memory-share-source",
            run_id="run-share",
            branch_id=source_branch.branch_id,
            stage_key=StageKey.BUILD,
            hypothesis="Promote the validated build insight",
            score=0.94,
            reason="Strong build evidence",
            kind=MemoryKind.ATOMIC,
            evidence=["benchmark trace"],
            outcome="passed",
            tags=["build", "insight"],
        ),
        service=memory_service,
    )

    result = rd_branch_share_apply(
        BranchShareApplyRequest(
            run_id="run-share",
            source_branch_id=source_branch.branch_id,
            target_branch_id=target_branch.branch_id,
            memory_id="memory-share-source",
            similarity=0.8,
            judge_allows_share=True,
        ),
        service=share_service,
    )
    target_view = memory_service.list_memory(
        MemoryListRequest(
            run_id="run-share",
            branch_id=target_branch.branch_id,
            stage_key=StageKey.BUILD,
            task_query="validated build insight",
            limit=5,
        )
    )

    assert result["structuredContent"]["owner_branch_id"] == source_branch.branch_id
    assert result["structuredContent"]["shared_namespace"] == MemoryNamespace.SHARED.value
    assert result["structuredContent"]["decision"]["kind"] == BranchDecisionKind.SHARE.value
    assert result["structuredContent"]["board"]["active_cards"][1]["shared_from_branch_ids"] == [
        source_branch.branch_id
    ]
    assert target_view.items[0].owner_branch_id == source_branch.branch_id
    assert target_view.items[0].shared_namespace is MemoryNamespace.SHARED
