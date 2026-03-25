"""Persistence boundary for V3-owned memory snapshots."""

from __future__ import annotations

from typing import Protocol

from rd_agent.contracts.memory import MemoryPromotionSnapshot, MemoryRecordSnapshot
from rd_agent.ports.state_store import ArtifactRecord


class MemoryStorePort(Protocol):
    """Port for writing and reading canonical V3 memory state."""

    def write_memory_record(self, record: MemoryRecordSnapshot) -> ArtifactRecord: ...

    def write_memory_promotion(self, promotion: MemoryPromotionSnapshot) -> ArtifactRecord: ...

    def load_memory_record(
        self,
        memory_id: str,
        *,
        run_id: str | None = None,
        owner_branch_id: str | None = None,
    ) -> MemoryRecordSnapshot | None: ...

    def load_memory_promotion(
        self,
        memory_id: str,
        *,
        run_id: str | None = None,
        owner_branch_id: str | None = None,
    ) -> MemoryPromotionSnapshot | None: ...

    def list_branch_records(self, run_id: str, owner_branch_id: str) -> list[MemoryRecordSnapshot]: ...

    def list_shared_promotions(self, run_id: str) -> list[MemoryPromotionSnapshot]: ...


__all__ = ["MemoryStorePort"]
