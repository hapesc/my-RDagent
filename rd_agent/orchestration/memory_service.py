"""Phase 15 memory ranking and promotion policy."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from rd_agent.contracts.memory import MemoryNamespace, MemoryPromotionSnapshot, MemoryRecordSnapshot
from rd_agent.contracts.tool_io import (
    MemoryCreateRequest,
    MemoryGetRequest,
    MemoryGetResult,
    MemoryListRequest,
    MemoryListResult,
    MemoryPromoteRequest,
    MemoryResultItem,
)
from rd_agent.ports.memory_store import MemoryStorePort


@dataclass(frozen=True)
class _RankedMemory:
    item: MemoryResultItem
    rank_score: float


class MemoryService:
    """V3-owned retrieval and promotion policy for memory records."""

    def __init__(self, store: MemoryStorePort, *, shared_ratio: float = 0.25) -> None:
        self._store = store
        self._shared_ratio = shared_ratio

    def create_memory(self, request: MemoryCreateRequest) -> MemoryGetResult:
        record = MemoryRecordSnapshot(
            memory_id=request.memory_id or f"mem-{uuid4().hex[:12]}",
            run_id=request.run_id,
            owner_branch_id=request.branch_id,
            stage_key=request.stage_key,
            kind=request.kind,
            hypothesis=request.hypothesis,
            score=request.score,
            reason=request.reason,
            evidence=request.evidence,
            outcome=request.outcome,
            tags=request.tags,
        )
        self._store.write_memory_record(record)
        return self._to_get_result(record)

    def get_memory(self, request: MemoryGetRequest) -> MemoryGetResult:
        record = self._store.load_memory_record(
            request.memory_id,
            run_id=request.run_id,
            owner_branch_id=request.owner_branch_id,
        )
        if record is None:
            raise KeyError(f"memory not found: {request.memory_id}")
        promotion = self._store.load_memory_promotion(
            request.memory_id,
            run_id=record.run_id,
            owner_branch_id=record.owner_branch_id,
        )
        return self._to_get_result(record, promotion, source_namespace=MemoryNamespace.BRANCH)

    def list_memory(self, request: MemoryListRequest) -> MemoryListResult:
        local_records = self._store.list_branch_records(request.run_id, request.branch_id)
        shared_records = self._shared_candidates(request.run_id, request.branch_id)

        ranked_local = sorted(
            (
                self._rank_record(
                    record, request.task_query, request.stage_key, source_namespace=MemoryNamespace.BRANCH
                )
                for record in local_records
            ),
            key=lambda ranked: ranked.rank_score,
            reverse=True,
        )
        ranked_shared = sorted(
            (
                self._rank_record(
                    record,
                    request.task_query,
                    request.stage_key,
                    source_namespace=MemoryNamespace.SHARED,
                    promotion=promotion,
                )
                for record, promotion in shared_records
            ),
            key=lambda ranked: ranked.rank_score,
            reverse=True,
        )

        shared_limit = max(1, int(request.limit * self._shared_ratio))
        selected_items = [ranked.item for ranked in ranked_local[: request.limit]]
        remaining_slots = max(request.limit - len(selected_items), 0)
        if remaining_slots:
            shared_count = min(remaining_slots, shared_limit, len(ranked_shared))
            selected_items.extend(ranked.item for ranked in ranked_shared[:shared_count])

        return MemoryListResult(
            run_id=request.run_id,
            branch_id=request.branch_id,
            items=selected_items,
        )

    def promote_memory(self, request: MemoryPromoteRequest) -> MemoryGetResult:
        record = self._store.load_memory_record(
            request.memory_id,
            run_id=request.run_id,
            owner_branch_id=request.owner_branch_id,
        )
        if record is None:
            raise KeyError(f"memory not found: {request.memory_id}")

        can_promote = self._can_promote(record)
        if not can_promote:
            return MemoryGetResult(
                **self._to_item(record).model_dump(),
                can_promote=False,
            )

        promotion = MemoryPromotionSnapshot(
            memory_id=record.memory_id,
            run_id=record.run_id,
            owner_branch_id=record.owner_branch_id,
            promotion_reason=request.promotion_reason,
            promoted_by=request.promoted_by,
            promoted_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            shared_namespace=MemoryNamespace.SHARED,
        )
        self._store.write_memory_promotion(promotion)
        return MemoryGetResult(
            **self._to_item(record, promotion, source_namespace=MemoryNamespace.SHARED).model_dump(),
            can_promote=True,
        )

    def _shared_candidates(
        self,
        run_id: str,
        branch_id: str,
    ) -> list[tuple[MemoryRecordSnapshot, MemoryPromotionSnapshot]]:
        candidates: list[tuple[MemoryRecordSnapshot, MemoryPromotionSnapshot]] = []
        for promotion in self._store.list_shared_promotions(run_id):
            if promotion.owner_branch_id == branch_id:
                continue
            record = self._store.load_memory_record(
                promotion.memory_id,
                run_id=promotion.run_id,
                owner_branch_id=promotion.owner_branch_id,
            )
            if record is None or record.run_id != run_id:
                continue
            candidates.append((record, promotion))
        return candidates

    def _rank_record(
        self,
        record: MemoryRecordSnapshot,
        task_query: str,
        stage_key,
        *,
        source_namespace: MemoryNamespace,
        promotion: MemoryPromotionSnapshot | None = None,
    ) -> _RankedMemory:
        query_tokens = self._tokenize(task_query)
        record_tokens = self._record_tokens(record)
        overlap = len(query_tokens & record_tokens)
        stage_match = 1.0 if record.stage_key == stage_key else 0.0
        tag_overlap = len(query_tokens & set(record.tags))
        local_bonus = 1.0 if source_namespace is MemoryNamespace.BRANCH else 0.0
        shared_penalty = 0.2 if source_namespace is MemoryNamespace.SHARED else 0.0
        rank_score = (
            (record.score * 2.0)
            + (stage_match * 1.5)
            + (overlap * 0.25)
            + (tag_overlap * 0.2)
            + local_bonus
            - shared_penalty
        )
        return _RankedMemory(
            item=self._to_item(record, promotion, source_namespace=source_namespace),
            rank_score=rank_score,
        )

    def _can_promote(self, record: MemoryRecordSnapshot) -> bool:
        evidence = record.evidence or []
        outcome = (record.outcome or "").strip()
        support_score = record.score + (0.2 * len(evidence)) + (0.3 if outcome else 0.0)
        return bool(evidence or outcome) and support_score >= 0.9

    def _to_item(
        self,
        record: MemoryRecordSnapshot,
        promotion: MemoryPromotionSnapshot | None = None,
        *,
        source_namespace: MemoryNamespace = MemoryNamespace.BRANCH,
    ) -> MemoryResultItem:
        return MemoryResultItem(
            memory_id=record.memory_id,
            run_id=record.run_id,
            owner_branch_id=record.owner_branch_id,
            stage_key=record.stage_key,
            kind=record.kind,
            hypothesis=record.hypothesis,
            score=record.score,
            reason=record.reason,
            evidence=record.evidence,
            outcome=record.outcome,
            tags=record.tags,
            source_namespace=source_namespace,
            shared_namespace=promotion.shared_namespace if promotion is not None else None,
            promotion_reason=promotion.promotion_reason if promotion is not None else None,
        )

    def _to_get_result(
        self,
        record: MemoryRecordSnapshot,
        promotion: MemoryPromotionSnapshot | None = None,
        *,
        can_promote: bool | None = None,
        source_namespace: MemoryNamespace = MemoryNamespace.BRANCH,
    ) -> MemoryGetResult:
        return MemoryGetResult(
            **self._to_item(record, promotion, source_namespace=source_namespace).model_dump(),
            can_promote=can_promote,
        )

    @staticmethod
    def _tokenize(value: str) -> set[str]:
        return {token.strip(".,:;!?").lower() for token in value.split() if token.strip(".,:;!?")}

    def _record_tokens(self, record: MemoryRecordSnapshot) -> set[str]:
        tokens: set[str] = set()
        for value in [
            record.hypothesis,
            record.reason,
            record.outcome or "",
            *record.tags,
            *self._flatten(record.evidence),
        ]:
            tokens.update(self._tokenize(value))
        return tokens

    @staticmethod
    def _flatten(values: Iterable[str] | None) -> list[str]:
        return list(values or [])


__all__ = ["MemoryService"]
