from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from v3.contracts.memory import (
    MemoryKind,
    MemoryNamespace,
    MemoryPromotionSnapshot,
    MemoryRecordSnapshot,
)
from v3.contracts.stage import StageKey
from v3.contracts.tool_io import MemoryCreateRequest, MemoryGetRequest, MemoryPromoteRequest
from v3.ports import MemoryStorePort


class _RecordingMemoryStore:
    def __init__(self) -> None:
        self.records: dict[str, MemoryRecordSnapshot] = {}
        self.promotions: dict[str, MemoryPromotionSnapshot] = {}

    def write_memory_record(self, record: MemoryRecordSnapshot) -> None:
        self.records[record.memory_id] = record

    def write_memory_promotion(self, promotion: MemoryPromotionSnapshot) -> None:
        self.promotions[promotion.memory_id] = promotion

    def load_memory_record(
        self,
        memory_id: str,
        *,
        run_id: str | None = None,
        owner_branch_id: str | None = None,
    ) -> MemoryRecordSnapshot | None:
        record = self.records.get(memory_id)
        if record is None:
            return None
        if run_id is not None and record.run_id != run_id:
            return None
        if owner_branch_id is not None and record.owner_branch_id != owner_branch_id:
            return None
        return record

    def load_memory_promotion(
        self,
        memory_id: str,
        *,
        run_id: str | None = None,
        owner_branch_id: str | None = None,
    ) -> MemoryPromotionSnapshot | None:
        promotion = self.promotions.get(memory_id)
        if promotion is None:
            return None
        if run_id is not None and promotion.run_id != run_id:
            return None
        if owner_branch_id is not None and promotion.owner_branch_id != owner_branch_id:
            return None
        return promotion

    def list_branch_records(self, run_id: str, owner_branch_id: str) -> list[MemoryRecordSnapshot]:
        return [
            record
            for record in self.records.values()
            if record.run_id == run_id and record.owner_branch_id == owner_branch_id
        ]

    def list_shared_promotions(self, run_id: str) -> list[MemoryPromotionSnapshot]:
        return [promotion for promotion in self.promotions.values() if promotion.run_id == run_id]


def test_memory_record_snapshot_persists_owner_branch_payload() -> None:
    store: MemoryStorePort = _RecordingMemoryStore()
    record = MemoryRecordSnapshot(
        memory_id="memory-001",
        run_id="run-001",
        owner_branch_id="branch-001",
        stage_key=StageKey.FRAMING,
        kind=MemoryKind.ATOMIC,
        hypothesis="Users prefer the lighter-weight retry path.",
        score=0.82,
        reason="The branch completed framing with a tighter execution plan.",
        evidence=["artifact-001"],
        outcome="prioritize-for-build",
        tags=["framing", "primary"],
    )

    store.write_memory_record(record)

    persisted = store.load_memory_record("memory-001")

    assert persisted == record
    assert persisted is not None
    assert persisted.owner_branch_id == "branch-001"
    assert persisted.evidence == ["artifact-001"]
    assert persisted.tags == ["framing", "primary"]


def test_stage_summary_memory_record_round_trips() -> None:
    store: MemoryStorePort = _RecordingMemoryStore()
    record = MemoryRecordSnapshot(
        memory_id="memory-stage-summary-001",
        run_id="run-001",
        owner_branch_id="branch-001",
        stage_key=StageKey.SYNTHESIZE,
        kind=MemoryKind.STAGE_SUMMARY,
        hypothesis="Stage summary keeps cross-step findings intact.",
        score=0.91,
        reason="Synthesis captured the strongest verified outcome for the branch.",
        evidence=None,
        outcome="ship-summary",
        tags=["summary", "synthesize"],
    )
    promotion = MemoryPromotionSnapshot(
        memory_id="memory-stage-summary-001",
        run_id="run-001",
        owner_branch_id="branch-001",
        promotion_reason="Verified summary should be visible in the shared layer.",
        promoted_by="reviewer",
        promoted_at="2026-03-20T11:15:00Z",
        shared_namespace=MemoryNamespace.SHARED,
    )

    store.write_memory_record(record)
    store.write_memory_promotion(promotion)

    assert store.list_branch_records("run-001", "branch-001") == [record]
    assert store.list_shared_promotions("run-001") == [promotion]
    assert store.load_memory_record("memory-stage-summary-001") == record
    assert store.load_memory_promotion("memory-stage-summary-001") == promotion


def test_memory_requests_accept_optional_scope_for_duplicate_disambiguation() -> None:
    request = MemoryGetRequest(
        memory_id="memory-001",
        run_id="run-001",
        owner_branch_id="branch-001",
    )
    promote_request = MemoryPromoteRequest(
        memory_id="memory-001",
        run_id="run-001",
        owner_branch_id="branch-001",
        promoted_by="reviewer-1",
        promotion_reason="Verified in the intended scope.",
    )

    assert request.run_id == "run-001"
    assert request.owner_branch_id == "branch-001"
    assert promote_request.run_id == "run-001"
    assert promote_request.owner_branch_id == "branch-001"


def test_memory_state_store_writes_branch_local_and_shared_namespaces(tmp_path: Path) -> None:
    from v3.orchestration.memory_state_store import MemoryStateStore

    store = MemoryStateStore(tmp_path / "state")
    record = MemoryRecordSnapshot(
        memory_id="memory-001",
        run_id="run-001",
        owner_branch_id="branch-001",
        stage_key=StageKey.FRAMING,
        kind=MemoryKind.ATOMIC,
        hypothesis="Branch-local framing note should stay under the owner branch path.",
        score=0.75,
        reason="The local branch found the cleanest framing approach.",
        evidence=["artifact-001"],
        outcome="local-keep",
        tags=["framing", "local"],
    )
    promotion = MemoryPromotionSnapshot(
        memory_id="memory-001",
        run_id="run-001",
        owner_branch_id="branch-001",
        promotion_reason="The framing result is strong enough to share across branches.",
        promoted_by="planner",
        promoted_at="2026-03-20T11:30:00Z",
        shared_namespace=MemoryNamespace.SHARED,
    )

    record_receipt = store.write_memory_record(record)
    promotion_receipt = store.write_memory_promotion(promotion)

    branch_record_path = (
        tmp_path / "state" / "memory" / "run-001" / "branches" / "branch-001" / "records" / "memory-001.json"
    )
    shared_promotion_path = (
        tmp_path / "state" / "memory" / "run-001" / "shared" / "promotions" / "memory-001.json"
    )

    assert record_receipt.storage_uri == str(branch_record_path)
    assert promotion_receipt.storage_uri == str(shared_promotion_path)
    assert "memory/run-001/branches/branch-001/records" in record_receipt.storage_uri
    assert "memory/run-001/shared/promotions" in promotion_receipt.storage_uri
    assert json.loads(branch_record_path.read_text())["owner_branch_id"] == "branch-001"
    assert json.loads(shared_promotion_path.read_text())["shared_namespace"] == "shared"
    assert store.load_memory_record("memory-001") == record
    assert store.load_memory_promotion("memory-001") == promotion
    assert store.list_branch_records("run-001", "branch-001") == [record]
    assert store.list_shared_promotions("run-001") == [promotion]


@pytest.mark.parametrize("unsafe_memory_id", ["../escape", "..\\escape", "memory/*", "memory-[abc]", ".", ".."])
def test_memory_contracts_reject_unsafe_memory_ids(unsafe_memory_id: str) -> None:
    with pytest.raises(ValidationError, match="memory_id"):
        MemoryRecordSnapshot(
            memory_id=unsafe_memory_id,
            run_id="run-001",
            owner_branch_id="branch-001",
            stage_key=StageKey.FRAMING,
            kind=MemoryKind.ATOMIC,
            hypothesis="Unsafe ids must be rejected before persistence.",
            score=0.75,
            reason="Protect branch-local paths and later lookups.",
            evidence=["artifact-001"],
            outcome="local-keep",
            tags=["framing", "local"],
        )

    with pytest.raises(ValidationError, match="memory_id"):
        MemoryPromotionSnapshot(
            memory_id=unsafe_memory_id,
            run_id="run-001",
            owner_branch_id="branch-001",
            promotion_reason="Unsafe ids must not reach shared promotion paths.",
            promoted_by="planner",
            promoted_at="2026-03-20T11:30:00Z",
            shared_namespace=MemoryNamespace.SHARED,
        )

    with pytest.raises(ValidationError, match="memory_id"):
        MemoryCreateRequest(
            memory_id=unsafe_memory_id,
            run_id="run-001",
            branch_id="branch-001",
            stage_key=StageKey.FRAMING,
            hypothesis="Unsafe ids must be rejected at request validation.",
            score=0.75,
            reason="Protect create calls before service execution.",
        )

    with pytest.raises(ValidationError, match="memory_id"):
        MemoryGetRequest(memory_id=unsafe_memory_id)

    with pytest.raises(ValidationError, match="memory_id"):
        MemoryPromoteRequest(
            memory_id=unsafe_memory_id,
            promoted_by="reviewer-1",
            promotion_reason="Unsafe ids must not reach lookup paths.",
        )


@pytest.mark.parametrize("unsafe_memory_id", ["../escape", "memory/*"])
def test_memory_state_store_rejects_unsafe_lookup_ids(tmp_path: Path, unsafe_memory_id: str) -> None:
    from v3.orchestration.memory_state_store import MemoryStateStore

    store = MemoryStateStore(tmp_path / "state")

    with pytest.raises(ValueError, match="memory_id"):
        store.load_memory_record(unsafe_memory_id)

    with pytest.raises(ValueError, match="memory_id"):
        store.load_memory_promotion(unsafe_memory_id)
