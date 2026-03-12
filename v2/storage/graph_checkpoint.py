from __future__ import annotations

from typing import Any

from v2.storage.protocols import GraphCheckpointStore

try:
    from langgraph.checkpoint.base import create_checkpoint, empty_checkpoint
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:  # pragma: no cover - exercised via fallback path in tests
    MemorySaver = None
    create_checkpoint = None
    empty_checkpoint = None


class LangGraphCheckpointStore(GraphCheckpointStore):
    def __init__(self, saver: Any | None = None) -> None:
        self._saver = saver if saver is not None else (MemorySaver() if MemorySaver is not None else None)
        self._fallback: dict[str, dict] = {}

    @property
    def uses_langgraph(self) -> bool:
        return self._saver is not None

    def save(self, thread_id: str, data: dict) -> None:
        if self._saver is None:
            self._fallback[thread_id] = dict(data)
            return

        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        current = self._saver.get_tuple(config)
        base_checkpoint = current.checkpoint if current is not None else empty_checkpoint()
        current_version = base_checkpoint["channel_versions"].get("state")
        next_version = self._saver.get_next_version(current_version, None)
        checkpoint = create_checkpoint(base_checkpoint, None, step=_extract_step(data))
        checkpoint["channel_values"] = {"state": dict(data)}
        checkpoint["channel_versions"] = {**base_checkpoint["channel_versions"], "state": next_version}
        self._saver.put(config, checkpoint, {"source": "update"}, {"state": next_version})

    def load(self, thread_id: str) -> dict | None:
        if self._saver is None:
            data = self._fallback.get(thread_id)
            return None if data is None else dict(data)

        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        checkpoint_tuple = self._saver.get_tuple(config)
        if checkpoint_tuple is None:
            return None
        state = checkpoint_tuple.checkpoint.get("channel_values", {}).get("state")
        return None if state is None else dict(state)


class MemoryGraphCheckpoint(LangGraphCheckpointStore):
    """In-memory graph checkpoint store for tests and local development."""


def _extract_step(data: dict) -> int:
    step = data.get("step", data.get("loop_iteration", 0))
    return step if isinstance(step, int) else 0


__all__ = ["LangGraphCheckpointStore", "MemoryGraphCheckpoint"]
