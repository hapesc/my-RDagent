"""Filesystem-backed persistence for V3 memory records and promotions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from v3.contracts.memory import MemoryPromotionSnapshot, MemoryRecordSnapshot, validate_memory_id
from v3.orchestration.branch_isolation_service import BranchIsolationService
from v3.ports.memory_store import MemoryStorePort
from v3.ports.state_store import ArtifactRecord

ModelT = TypeVar("ModelT", bound=BaseModel)


class MemoryStateStore(MemoryStorePort):
    """Canonical JSON persistence for Phase 15 memory state."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._isolation = BranchIsolationService(self._root)

    def write_memory_record(self, record: MemoryRecordSnapshot) -> ArtifactRecord:
        path = self._isolation.memory_root(record.run_id, record.owner_branch_id) / "records" / f"{record.memory_id}.json"
        self._write_model(path, record)
        return ArtifactRecord(
            artifact_id=record.memory_id,
            storage_uri=str(path),
            media_type="application/json",
        )

    def write_memory_promotion(self, promotion: MemoryPromotionSnapshot) -> ArtifactRecord:
        path = self._isolation.shared_memory_root(promotion.run_id) / "promotions" / f"{promotion.memory_id}.json"
        self._write_model(path, promotion)
        return ArtifactRecord(
            artifact_id=f"promotion:{promotion.memory_id}",
            storage_uri=str(path),
            media_type="application/json",
        )

    def load_memory_record(
        self,
        memory_id: str,
        *,
        run_id: str | None = None,
        owner_branch_id: str | None = None,
    ) -> MemoryRecordSnapshot | None:
        validate_memory_id(memory_id)
        matches = self._record_matches(memory_id, run_id=run_id, owner_branch_id=owner_branch_id)
        if not matches:
            return None
        if len(matches) > 1:
            raise KeyError(f"ambiguous memory record lookup for {memory_id}")
        return self._read_model(matches[0], MemoryRecordSnapshot)

    def load_memory_promotion(
        self,
        memory_id: str,
        *,
        run_id: str | None = None,
        owner_branch_id: str | None = None,
    ) -> MemoryPromotionSnapshot | None:
        validate_memory_id(memory_id)
        matches = self._promotion_matches(memory_id, run_id=run_id, owner_branch_id=owner_branch_id)
        if not matches:
            return None
        if len(matches) > 1:
            raise KeyError(f"ambiguous memory promotion lookup for {memory_id}")
        return self._read_model(matches[0], MemoryPromotionSnapshot)

    def list_branch_records(self, run_id: str, owner_branch_id: str) -> list[MemoryRecordSnapshot]:
        base = self._isolation.memory_root(run_id, owner_branch_id) / "records"
        if not base.exists():
            return []
        records = [
            MemoryRecordSnapshot.model_validate(json.loads(path.read_text()))
            for path in sorted(base.glob("*.json"))
        ]
        return [record for record in records if record.run_id == run_id and record.owner_branch_id == owner_branch_id]

    def list_shared_promotions(self, run_id: str) -> list[MemoryPromotionSnapshot]:
        base = self._isolation.shared_memory_root(run_id) / "promotions"
        if not base.exists():
            return []
        promotions = [
            MemoryPromotionSnapshot.model_validate(json.loads(path.read_text()))
            for path in sorted(base.glob("*.json"))
        ]
        return [promotion for promotion in promotions if promotion.run_id == run_id]

    def _write_model(self, path: Path, model: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model.model_dump_json(indent=2) + "\n")

    def _record_matches(
        self,
        memory_id: str,
        *,
        run_id: str | None = None,
        owner_branch_id: str | None = None,
    ) -> list[Path]:
        if run_id is not None and owner_branch_id is not None:
            return [
                self._isolation.memory_root(run_id, owner_branch_id) / "records" / f"{memory_id}.json"
            ]
        run_glob = run_id or "*"
        branch_glob = owner_branch_id or "*"
        return sorted(self._root.glob(f"memory/{run_glob}/branches/{branch_glob}/records/{memory_id}.json"))

    def _promotion_matches(
        self,
        memory_id: str,
        *,
        run_id: str | None = None,
        owner_branch_id: str | None = None,
    ) -> list[Path]:
        run_glob = run_id or "*"
        matches = sorted(self._root.glob(f"memory/{run_glob}/shared/promotions/{memory_id}.json"))
        if owner_branch_id is None:
            return matches

        return [
            path
            for path in matches
            if (
                promotion := self._read_model(path, MemoryPromotionSnapshot)
            ) is not None and promotion.owner_branch_id == owner_branch_id
        ]

    def _read_model(self, path: Path, model_type: type[ModelT]) -> ModelT | None:
        if not path.exists():
            return None
        return model_type.model_validate(json.loads(path.read_text()))


__all__ = ["MemoryStateStore"]
