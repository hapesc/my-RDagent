from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path


def _load_coordinator_class():
    module = import_module("v2.storage.checkpoint_coordinator")
    return module.CheckpointBlobCoordinator


def test_checkpoint_blob_coordinator_save_restore_round_trip(tmp_path: Path) -> None:
    coordinator = _load_coordinator_class()(tmp_path / "checkpoints", tmp_path / "blobs")

    checkpoint_id = coordinator.save("loop-0001-feedback", b"fake-zip", {"step": "feedback"})

    restored_workspace, restored_state = coordinator.restore(checkpoint_id)

    assert restored_workspace == b"fake-zip"
    assert restored_state == {"step": "feedback"}


def test_checkpoint_blob_coordinator_checkpoint_id_contains_name_and_metadata(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "checkpoints"
    coordinator = _load_coordinator_class()(checkpoint_dir, tmp_path / "blobs")

    checkpoint_id = coordinator.save("loop-0001-feedback", b"fake-zip", {"step": "feedback"})
    metadata = json.loads((checkpoint_dir / f"{checkpoint_id}.json").read_text(encoding="utf-8"))

    assert checkpoint_id.startswith("loop-0001-feedback-")
    assert "loop-0001-feedback" in checkpoint_id
    assert metadata["checkpoint_id"] == checkpoint_id
    assert metadata["name"] == "loop-0001-feedback"
    assert metadata["state"] == {"step": "feedback"}
    assert metadata["blob_ref"].endswith("/loop-0001-feedback.zip")
