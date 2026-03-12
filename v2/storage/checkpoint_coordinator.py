from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from v2.storage.blob_store import FileBlobStore


class CheckpointBlobCoordinator:
    def __init__(self, checkpoint_dir: str, blob_dir: str) -> None:
        self._checkpoint_dir = Path(checkpoint_dir)
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._blob_store = FileBlobStore(blob_dir)

    def save(self, name: str, workspace_data: bytes, state: dict) -> str:
        blob_ref = self._blob_store.save(workspace_data, f"{name}.zip")
        checkpoint_id = f"{name}-{uuid4().hex[:8]}"
        metadata = {
            "checkpoint_id": checkpoint_id,
            "name": name,
            "blob_ref": blob_ref,
            "state": state,
        }
        checkpoint_path = self._checkpoint_dir / f"{checkpoint_id}.json"
        checkpoint_path.write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")
        return checkpoint_id

    def restore(self, checkpoint_id: str) -> tuple[bytes, dict]:
        checkpoint_path = self._checkpoint_dir / f"{checkpoint_id}.json"
        metadata = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        workspace_data = self._blob_store.load(metadata["blob_ref"])
        return workspace_data, metadata["state"]


__all__ = ["CheckpointBlobCoordinator"]
