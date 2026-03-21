from __future__ import annotations

from datetime import UTC, datetime

import pytest

from v3.contracts.memory import MemoryKind, MemoryNamespace, MemoryPromotionSnapshot, MemoryRecordSnapshot
from v3.contracts.stage import StageKey
from v3.contracts.tool_io import MemoryCreateRequest, MemoryGetRequest, MemoryListRequest, MemoryPromoteRequest
from v3.orchestration.memory_service import MemoryService
from v3.orchestration.memory_state_store import MemoryStateStore
from v3.tools.memory_tools import rd_memory_create, rd_memory_get, rd_memory_list, rd_memory_promote


def _record(
    memory_id: str,
    owner_branch_id: str,
    *,
    stage_key: StageKey,
    hypothesis: str,
    score: float,
    reason: str,
    evidence: list[str] | None = None,
    outcome: str | None = None,
    tags: list[str] | None = None,
) -> MemoryRecordSnapshot:
    return MemoryRecordSnapshot(
        memory_id=memory_id,
        run_id="run-001",
        owner_branch_id=owner_branch_id,
        stage_key=stage_key,
        kind=MemoryKind.ATOMIC,
        hypothesis=hypothesis,
        score=score,
        reason=reason,
        evidence=evidence,
        outcome=outcome,
        tags=tags or [],
    )


def _promotion(memory_id: str, owner_branch_id: str, *, promotion_reason: str) -> MemoryPromotionSnapshot:
    return MemoryPromotionSnapshot(
        memory_id=memory_id,
        run_id="run-001",
        owner_branch_id=owner_branch_id,
        promotion_reason=promotion_reason,
        promoted_by="reviewer-1",
        promoted_at="2026-03-20T11:30:00Z",
        shared_namespace=MemoryNamespace.SHARED,
    )


def test_memory_service_returns_branch_local_first_with_shared_cap(tmp_path) -> None:
    store = MemoryStateStore(tmp_path)
    service = MemoryService(store)

    local_records = [
        _record(
            "local-verify-1",
            "branch-a",
            stage_key=StageKey.VERIFY,
            hypothesis="Verify branch-a experiment with branch-local evidence",
            score=0.82,
            reason="Directly targets verify stage",
            evidence=["benchmark trace"],
            outcome="passed",
            tags=["verify", "experiment"],
        ),
        _record(
            "local-verify-2",
            "branch-a",
            stage_key=StageKey.VERIFY,
            hypothesis="Verify branch-a regression fix against prior failure",
            score=0.78,
            reason="Still verify relevant",
            evidence=["regression note"],
            tags=["verify", "regression"],
        ),
        _record(
            "local-build-1",
            "branch-a",
            stage_key=StageKey.BUILD,
            hypothesis="Build branch-a artifact with reusable harness",
            score=0.91,
            reason="High score but weaker stage match",
            tags=["build", "artifact"],
        ),
    ]
    shared_records = [
        _record(
            "shared-verify-1",
            "branch-b",
            stage_key=StageKey.VERIFY,
            hypothesis="Verify a cross-branch fix with matching experiment evidence",
            score=0.93,
            reason="Strong shared verify note",
            evidence=["experiment report"],
            outcome="stable",
            tags=["verify", "experiment"],
        ),
        _record(
            "shared-verify-2",
            "branch-c",
            stage_key=StageKey.VERIFY,
            hypothesis="Verify another cross-branch note that should be capped",
            score=0.95,
            reason="Would outrank locals if cap policy failed",
            evidence=["second report"],
            outcome="stable",
            tags=["verify", "experiment"],
        ),
    ]

    for record in [*local_records, *shared_records]:
        store.write_memory_record(record)
    for record in shared_records:
        store.write_memory_promotion(
            _promotion(record.memory_id, record.owner_branch_id, promotion_reason="Matched verify evidence")
        )

    result = service.list_memory(
        MemoryListRequest(
            run_id="run-001",
            branch_id="branch-a",
            stage_key=StageKey.VERIFY,
            task_query="verify experiment evidence",
            limit=4,
        )
    )

    assert [item.memory_id for item in result.items] == [
        "local-verify-1",
        "local-verify-2",
        "local-build-1",
        "shared-verify-1",
    ]
    assert [item.source_namespace for item in result.items[:3]] == [
        MemoryNamespace.BRANCH,
        MemoryNamespace.BRANCH,
        MemoryNamespace.BRANCH,
    ]
    assert result.items[3].source_namespace is MemoryNamespace.SHARED
    assert result.items[3].owner_branch_id == "branch-b"
    assert result.items[3].promotion_reason == "Matched verify evidence"
    assert result.items[3].score >= result.items[2].score


def test_memory_promotion_requires_supporting_evidence_or_outcome(tmp_path) -> None:
    store = MemoryStateStore(tmp_path)
    service = MemoryService(store)

    store.write_memory_record(
        _record(
            "memory-no-proof",
            "branch-a",
            stage_key=StageKey.VERIFY,
            hypothesis="High score alone should not force promotion",
            score=0.98,
            reason="Speculative note with no supporting proof",
            tags=["verify"],
        )
    )

    result = service.promote_memory(
        MemoryPromoteRequest(
            memory_id="memory-no-proof",
            promoted_by="reviewer-1",
            promotion_reason="manual promote request",
        )
    )

    assert result.can_promote is False
    assert result.shared_namespace is None
    assert result.promotion_reason is None
    assert store.load_memory_promotion("memory-no-proof") is None


def test_memory_promote_preserves_owner_branch_and_promotion_reason(tmp_path) -> None:
    store = MemoryStateStore(tmp_path)
    service = MemoryService(store)

    create_response = rd_memory_create(
        MemoryCreateRequest(
            memory_id="memory-proof",
            run_id="run-001",
            branch_id="branch-a",
            stage_key=StageKey.VERIFY,
            hypothesis="Verify memory with supporting evidence",
            score=0.91,
            reason="Observed stable verify result",
            evidence=["benchmark report"],
            outcome="passed",
            tags=["verify", "benchmark"],
        ),
        service=service,
    )

    assert create_response["structuredContent"]["owner_branch_id"] == "branch-a"

    promote_response = rd_memory_promote(
        MemoryPromoteRequest(
            memory_id="memory-proof",
            promoted_by="reviewer-1",
            promotion_reason="Stable benchmark passed",
        ),
        service=service,
    )

    assert promote_response["structuredContent"]["can_promote"] is True
    assert promote_response["structuredContent"]["owner_branch_id"] == "branch-a"
    assert promote_response["structuredContent"]["promotion_reason"] == "Stable benchmark passed"
    assert promote_response["structuredContent"]["shared_namespace"] == MemoryNamespace.SHARED.value
    assert "branch-a" in promote_response["content"][0]["text"]
    assert "Stable benchmark passed" in promote_response["content"][0]["text"]

    get_response = rd_memory_get(MemoryGetRequest(memory_id="memory-proof"), service=service)
    assert get_response["structuredContent"]["owner_branch_id"] == "branch-a"
    assert get_response["structuredContent"]["source_namespace"] == MemoryNamespace.BRANCH.value
    assert get_response["structuredContent"]["shared_namespace"] == MemoryNamespace.SHARED.value
    assert get_response["structuredContent"]["promotion_reason"] == "Stable benchmark passed"

    get_result = service.get_memory(MemoryGetRequest(memory_id="memory-proof"))
    assert get_result.owner_branch_id == "branch-a"
    assert get_result.source_namespace is MemoryNamespace.BRANCH
    assert get_result.shared_namespace is MemoryNamespace.SHARED
    assert get_result.promotion_reason == "Stable benchmark passed"


def test_memory_tools_round_trip_without_cross_branch_duplication(tmp_path) -> None:
    store = MemoryStateStore(tmp_path)
    service = MemoryService(store)

    rd_memory_create(
        MemoryCreateRequest(
            memory_id="memory-local-only",
            run_id="run-001",
            branch_id="branch-a",
            stage_key=StageKey.BUILD,
            hypothesis="Build-only local note",
            score=0.74,
            reason="Useful for branch-a build work",
            tags=["build"],
        ),
        service=service,
    )

    branch_a_response = rd_memory_list(
        MemoryListRequest(
            run_id="run-001",
            branch_id="branch-a",
            stage_key=StageKey.BUILD,
            task_query="build local note",
            limit=5,
        ),
        service=service,
    )
    assert [item["memory_id"] for item in branch_a_response["structuredContent"]["items"]] == ["memory-local-only"]

    branch_b_response = rd_memory_list(
        MemoryListRequest(
            run_id="run-001",
            branch_id="branch-b",
            stage_key=StageKey.BUILD,
            task_query="build local note",
            limit=5,
        ),
        service=service,
    )
    assert branch_b_response["structuredContent"]["items"] == []


def test_phase16_share_apply_uses_phase15_memory_contract_without_cross_branch_duplication(tmp_path) -> None:
    from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
    from v3.contracts.run import RunBoardSnapshot, RunStatus
    from v3.contracts.stage import StageSnapshot, StageStatus
    from v3.contracts.tool_io import BranchShareApplyRequest
    from v3.orchestration.artifact_state_store import ArtifactStateStore
    from v3.orchestration.branch_board_service import BranchBoardService
    from v3.orchestration.branch_share_service import BranchShareService
    from v3.tools.exploration_tools import rd_branch_share_apply

    store = MemoryStateStore(tmp_path / "memory")
    service = MemoryService(store)
    state_store = ArtifactStateStore(tmp_path / "state")
    share_service = BranchShareService(
        state_store=state_store,
        memory_service=service,
        board_service=BranchBoardService(state_store),
    )

    stage = StageSnapshot(
        stage_key=StageKey.BUILD,
        status=StageStatus.COMPLETED,
        summary="Build completed.",
        next_stage_key=StageKey.VERIFY,
    )
    source_branch = BranchSnapshot(
        branch_id="branch-source",
        run_id="run-001",
        label="source hypothesis",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.BUILD,
        stages=[stage],
        score=BranchScore(exploration_priority=0.7, result_quality=0.9, rationale="source score"),
        lineage=BranchLineage(source_summary="source"),
        artifact_ids=[],
    )
    target_branch = BranchSnapshot(
        branch_id="branch-target",
        run_id="run-001",
        label="target hypothesis",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.BUILD,
        stages=[stage],
        score=BranchScore(exploration_priority=0.6, result_quality=0.8, rationale="target score"),
        lineage=BranchLineage(source_summary="target"),
        artifact_ids=[],
    )
    for branch in [source_branch, target_branch]:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-001",
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
            memory_id="memory-shared",
            run_id="run-001",
            branch_id="branch-source",
            stage_key=StageKey.BUILD,
            hypothesis="Shared build insight",
            score=0.95,
            reason="Strong build result",
            evidence=["build trace"],
            outcome="passed",
            tags=["build", "shared"],
        ),
        service=service,
    )

    rd_branch_share_apply(
        BranchShareApplyRequest(
            run_id="run-001",
            source_branch_id="branch-source",
            target_branch_id="branch-target",
            memory_id="memory-shared",
            similarity=0.8,
            judge_allows_share=True,
        ),
        service=share_service,
    )

    branch_source_items = service.list_memory(
        MemoryListRequest(
            run_id="run-001",
            branch_id="branch-source",
            stage_key=StageKey.BUILD,
            task_query="shared build insight",
            limit=5,
        )
    )
    branch_target_items = service.list_memory(
        MemoryListRequest(
            run_id="run-001",
            branch_id="branch-target",
            stage_key=StageKey.BUILD,
            task_query="shared build insight",
            limit=5,
        )
    )

    assert [item.memory_id for item in branch_source_items.items] == ["memory-shared"]
    assert [item.memory_id for item in branch_target_items.items] == ["memory-shared"]
    assert branch_target_items.items[0].owner_branch_id == "branch-source"
    assert branch_target_items.items[0].shared_namespace is MemoryNamespace.SHARED


def test_memory_list_uses_promotion_scope_when_duplicate_memory_ids_exist(tmp_path) -> None:
    store = MemoryStateStore(tmp_path)
    service = MemoryService(store)

    store.write_memory_record(
        _record(
            "shared-collision",
            "branch-b",
            stage_key=StageKey.VERIFY,
            hypothesis="Verify shared note for run-001",
            score=0.89,
            reason="Correct promoted memory for the current run",
            evidence=["run-001-report"],
            outcome="stable",
            tags=["verify", "shared"],
        )
    )
    store.write_memory_record(
        MemoryRecordSnapshot(
            memory_id="shared-collision",
            run_id="run-999",
            owner_branch_id="branch-z",
            stage_key=StageKey.BUILD,
            kind=MemoryKind.ATOMIC,
            hypothesis="Conflicting memory from another run",
            score=0.2,
            reason="Should never satisfy run-001 shared lookup",
            evidence=["run-999-report"],
            outcome="ignore",
            tags=["build"],
        )
    )
    store.write_memory_promotion(
        _promotion("shared-collision", "branch-b", promotion_reason="Verified for run-001 sharing")
    )

    result = service.list_memory(
        MemoryListRequest(
            run_id="run-001",
            branch_id="branch-a",
            stage_key=StageKey.VERIFY,
            task_query="verify shared",
            limit=3,
        )
    )

    assert [item.memory_id for item in result.items] == ["shared-collision"]
    assert result.items[0].run_id == "run-001"
    assert result.items[0].owner_branch_id == "branch-b"
    assert result.items[0].source_namespace is MemoryNamespace.SHARED


def test_memory_promote_rejects_ambiguous_memory_ids_across_scopes(tmp_path) -> None:
    store = MemoryStateStore(tmp_path)
    service = MemoryService(store)

    store.write_memory_record(
        _record(
            "memory-collision",
            "branch-a",
            stage_key=StageKey.VERIFY,
            hypothesis="Branch-a verify note",
            score=0.94,
            reason="Eligible record in run-001",
            evidence=["branch-a-report"],
            outcome="passed",
            tags=["verify"],
        )
    )
    store.write_memory_record(
        MemoryRecordSnapshot(
            memory_id="memory-collision",
            run_id="run-002",
            owner_branch_id="branch-b",
            stage_key=StageKey.VERIFY,
            kind=MemoryKind.ATOMIC,
            hypothesis="Another record with the same id",
            score=0.95,
            reason="Creates an ambiguous unscoped lookup",
            evidence=["branch-b-report"],
            outcome="passed",
            tags=["verify"],
        )
    )

    with pytest.raises(KeyError, match="ambiguous"):
        service.promote_memory(
            MemoryPromoteRequest(
                memory_id="memory-collision",
                promoted_by="reviewer-1",
                promotion_reason="Should not resolve by glob order",
            )
        )


def test_memory_get_and_promote_support_scope_for_duplicate_memory_ids(tmp_path) -> None:
    store = MemoryStateStore(tmp_path)
    service = MemoryService(store)

    store.write_memory_record(
        _record(
            "memory-collision",
            "branch-a",
            stage_key=StageKey.VERIFY,
            hypothesis="Branch-a verify note",
            score=0.94,
            reason="Eligible record in run-001",
            evidence=["branch-a-report"],
            outcome="passed",
            tags=["verify"],
        )
    )
    store.write_memory_record(
        MemoryRecordSnapshot(
            memory_id="memory-collision",
            run_id="run-002",
            owner_branch_id="branch-b",
            stage_key=StageKey.VERIFY,
            kind=MemoryKind.ATOMIC,
            hypothesis="Another record with the same id",
            score=0.95,
            reason="Creates an ambiguous unscoped lookup",
            evidence=["branch-b-report"],
            outcome="passed",
            tags=["verify"],
        )
    )

    get_result = service.get_memory(
        MemoryGetRequest(
            memory_id="memory-collision",
            run_id="run-001",
            owner_branch_id="branch-a",
        )
    )
    assert get_result.run_id == "run-001"
    assert get_result.owner_branch_id == "branch-a"

    promote_result = service.promote_memory(
        MemoryPromoteRequest(
            memory_id="memory-collision",
            run_id="run-001",
            owner_branch_id="branch-a",
            promoted_by="reviewer-1",
            promotion_reason="Scoped duplicate resolution",
        )
    )

    assert promote_result.can_promote is True
    promotion = store.load_memory_promotion(
        "memory-collision",
        run_id="run-001",
        owner_branch_id="branch-a",
    )
    assert promotion is not None
    assert promotion.owner_branch_id == "branch-a"
    assert promotion.promotion_reason == "Scoped duplicate resolution"


def test_memory_promote_records_real_timestamp(tmp_path) -> None:
    store = MemoryStateStore(tmp_path)
    service = MemoryService(store)

    store.write_memory_record(
        _record(
            "memory-real-time",
            "branch-a",
            stage_key=StageKey.VERIFY,
            hypothesis="Promotion should capture real time",
            score=0.92,
            reason="Has evidence and outcome",
            evidence=["timing-report"],
            outcome="passed",
            tags=["verify"],
        )
    )

    before = datetime.now(UTC)
    result = service.promote_memory(
        MemoryPromoteRequest(
            memory_id="memory-real-time",
            promoted_by="reviewer-1",
            promotion_reason="Timestamp regression check",
        )
    )
    after = datetime.now(UTC)

    promotion = store.load_memory_promotion("memory-real-time")

    assert result.can_promote is True
    assert promotion is not None
    promoted_at = datetime.fromisoformat(promotion.promoted_at.replace("Z", "+00:00"))
    assert before <= promoted_at <= after
    assert promotion.promoted_at != "2026-03-20T12:00:00Z"


def test_memory_tool_text_exposes_namespace_owner_and_promotion_reason(tmp_path) -> None:
    store = MemoryStateStore(tmp_path)
    service = MemoryService(store)

    rd_memory_create(
        MemoryCreateRequest(
            memory_id="memory-operator",
            run_id="run-001",
            branch_id="branch-a",
            stage_key=StageKey.VERIFY,
            hypothesis="Operator-facing memory text should expose scope",
            score=0.93,
            reason="Needs readable fallback text",
            evidence=["operator-report"],
            outcome="passed",
            tags=["verify", "operator"],
        ),
        service=service,
    )
    rd_memory_promote(
        MemoryPromoteRequest(
            memory_id="memory-operator",
            run_id="run-001",
            owner_branch_id="branch-a",
            promoted_by="reviewer-1",
            promotion_reason="Stable benchmark passed",
        ),
        service=service,
    )

    get_response = rd_memory_get(
        MemoryGetRequest(
            memory_id="memory-operator",
            run_id="run-001",
            owner_branch_id="branch-a",
        ),
        service=service,
    )
    get_text = get_response["content"][0]["text"]
    assert "local" in get_text.lower()
    assert "shared" in get_text.lower()
    assert "branch-a" in get_text
    assert "Stable benchmark passed" in get_text

    list_response = rd_memory_list(
        MemoryListRequest(
            run_id="run-001",
            branch_id="branch-b",
            stage_key=StageKey.VERIFY,
            task_query="operator verify benchmark",
            limit=5,
        ),
        service=service,
    )
    list_text = list_response["content"][0]["text"]
    assert "shared" in list_text.lower()
    assert "branch-a" in list_text
    assert "Stable benchmark passed" in list_text
