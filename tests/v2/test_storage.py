from __future__ import annotations

import json
from pathlib import Path
from typing import get_type_hints

import pytest

from v2.storage.blob_store import FileBlobStore, MemoryBlobStore
from v2.storage.event_log import JSONLEventLog
from v2.storage.graph_checkpoint import MemoryGraphCheckpoint
from v2.storage.protocols import BlobReferenceStore, EventLogStore, GraphCheckpointStore


def test_protocols_are_importable() -> None:
    assert GraphCheckpointStore is not None
    assert EventLogStore is not None
    assert BlobReferenceStore is not None


def test_protocol_method_signatures_are_stable() -> None:
    checkpoint_hints = get_type_hints(GraphCheckpointStore.save)
    assert checkpoint_hints == {"thread_id": str, "data": dict, "return": type(None)}

    checkpoint_load_hints = get_type_hints(GraphCheckpointStore.load)
    assert checkpoint_load_hints == {"thread_id": str, "return": dict | None}

    event_append_hints = get_type_hints(EventLogStore.append)
    assert event_append_hints == {"event": dict, "return": type(None)}

    event_read_hints = get_type_hints(EventLogStore.read_all)
    assert event_read_hints == {"return": list[dict]}

    blob_save_hints = get_type_hints(BlobReferenceStore.save)
    assert blob_save_hints == {"data": bytes, "name": str, "return": str}

    blob_load_hints = get_type_hints(BlobReferenceStore.load)
    assert blob_load_hints == {"ref": str, "return": bytes}


def test_memory_graph_checkpoint_round_trips_data() -> None:
    store = MemoryGraphCheckpoint()

    payload = {"loop": 1, "step": "coding"}
    store.save("thread-1", payload)

    assert store.load("thread-1") == payload


def test_memory_graph_checkpoint_returns_none_for_unknown_thread() -> None:
    store = MemoryGraphCheckpoint()

    assert store.load("missing") is None


def test_jsonl_event_log_appends_and_reads_all_events(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    store = JSONLEventLog(log_path)

    first = {"event": "proposal.generated", "seq": 1}
    second = {"event": "coding.completed", "seq": 2}
    store.append(first)
    store.append(second)

    assert store.read_all() == [first, second]
    assert [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()] == [first, second]


def test_jsonl_event_log_ignores_blank_lines_when_reading(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    log_path.write_text('{"event": 1}\n\n{"event": 2}\n', encoding="utf-8")

    store = JSONLEventLog(log_path)

    assert store.read_all() == [{"event": 1}, {"event": 2}]


def test_file_blob_store_round_trips_saved_bytes(tmp_path: Path) -> None:
    store = FileBlobStore(tmp_path)

    ref = store.save(b"zip-bytes", "workspace.zip")

    assert store.load(ref) == b"zip-bytes"
    assert (tmp_path / ref).read_bytes() == b"zip-bytes"


def test_file_blob_store_rejects_nested_names(tmp_path: Path) -> None:
    store = FileBlobStore(tmp_path)

    with pytest.raises(ValueError):
        store.save(b"zip-bytes", "nested/workspace.zip")


def test_memory_blob_store_round_trips_saved_bytes() -> None:
    store = MemoryBlobStore()

    ref = store.save(b"artifact", "artifact.zip")

    assert store.load(ref) == b"artifact"
    assert ref.endswith("/artifact.zip")
