"""Filesystem checkpoint store."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class CheckpointStoreConfig:
    """Configuration for filesystem checkpoint store."""

    root_dir: str = "/tmp/rd_agent_checkpoints"


class FileCheckpointStore:
    """Stores checkpoint payloads under per-run directories."""

    def __init__(self, config: CheckpointStoreConfig) -> None:
        self._config = config
        self._root = Path(config.root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        run_dir = self._root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _checkpoint_path(self, run_id: str, checkpoint_id: str) -> Path:
        return self._run_dir(run_id) / f"{checkpoint_id}.ckpt"

    def save_checkpoint(self, run_id: str, checkpoint_id: str, payload: bytes) -> str:
        path = self._checkpoint_path(run_id, checkpoint_id)
        path.write_bytes(payload)
        return str(path)

    def load_checkpoint(self, run_id: str, checkpoint_id: str) -> bytes:
        path = self._checkpoint_path(run_id, checkpoint_id)
        return path.read_bytes()

    def delete_checkpoint(self, run_id: str, checkpoint_id: str) -> bool:
        path = self._checkpoint_path(run_id, checkpoint_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_checkpoints(self, run_id: str) -> List[str]:
        run_dir = self._run_dir(run_id)
        checkpoints = [path.stem for path in run_dir.glob("*.ckpt") if path.is_file()]
        return sorted(checkpoints)
