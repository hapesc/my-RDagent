from __future__ import annotations

import importlib
from typing import Any

from v2.storage.protocols import GraphCheckpointStore


def _load_langgraph_checkpoint_symbols() -> tuple[Any | None, Any | None, Any | None]:
    try:
        checkpoint_base = importlib.import_module("langgraph.checkpoint.base")
        checkpoint_memory = importlib.import_module("langgraph.checkpoint.memory")
    except ImportError:  # pragma: no cover - exercised via fallback path in tests
        return None, None, None
    return (
        getattr(checkpoint_memory, "MemorySaver", None),
        getattr(checkpoint_base, "create_checkpoint", None),
        getattr(checkpoint_base, "empty_checkpoint", None),
    )


_MEMORY_SAVER, _CREATE_CHECKPOINT, _EMPTY_CHECKPOINT = _load_langgraph_checkpoint_symbols()


class LangGraphCheckpointStore(GraphCheckpointStore):
    def __init__(self, saver: Any | None = None) -> None:
        self._saver = saver if saver is not None else (_MEMORY_SAVER() if _MEMORY_SAVER is not None else None)
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
        if _CREATE_CHECKPOINT is None or _EMPTY_CHECKPOINT is None:
            self._fallback[thread_id] = dict(data)
            return

        base_checkpoint = current.checkpoint if current is not None else _EMPTY_CHECKPOINT()
        current_version = base_checkpoint["channel_versions"].get("state")
        next_version = self._saver.get_next_version(current_version, None)
        checkpoint = _CREATE_CHECKPOINT(base_checkpoint, None, step=_extract_step(data))
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
