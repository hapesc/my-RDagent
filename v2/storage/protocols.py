from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class GraphCheckpointStore(Protocol):
    def save(self, thread_id: str, data: dict) -> None: ...

    def load(self, thread_id: str) -> dict | None: ...


@runtime_checkable
class EventLogStore(Protocol):
    def append(self, event: dict) -> None: ...

    def read_all(self) -> list[dict]: ...


@runtime_checkable
class BlobReferenceStore(Protocol):
    def save(self, data: bytes, name: str) -> str: ...

    def load(self, ref: str) -> bytes: ...


__all__ = ["GraphCheckpointStore", "EventLogStore", "BlobReferenceStore"]
