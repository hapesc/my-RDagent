"""Storage interfaces for metadata, events, and checkpoints."""

from __future__ import annotations

from typing import Protocol

from data_models import Event, RunSession


class RunMetadataStore(Protocol):
    """Persistence contract for run session metadata."""

    def create_run(self, run_session: RunSession) -> None: ...

    def get_run(self, run_id: str) -> RunSession | None: ...

    def list_runs(self) -> list[RunSession]: ...


class EventMetadataStore(Protocol):
    """Persistence contract for append-only event stream."""

    def append_event(self, event: Event) -> None: ...

    def query_events(self, run_id: str | None = None, branch_id: str | None = None) -> list[Event]: ...


class CheckpointStore(Protocol):
    """Persistence contract for checkpoint binary payloads."""

    def save_checkpoint(self, run_id: str, checkpoint_id: str, payload: bytes) -> str: ...

    def load_checkpoint(self, run_id: str, checkpoint_id: str) -> bytes: ...

    def delete_checkpoint(self, run_id: str, checkpoint_id: str) -> bool: ...

    def list_checkpoints(self, run_id: str) -> list[str]: ...
