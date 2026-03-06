"""Workspace manager with checkpoint save/restore support."""

from __future__ import annotations

import hashlib
import io
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from core.path_safety import ensure_within_root, resolve_relative_to_root, validate_path_component
from core.storage import CheckpointStoreConfig, FileCheckpointStore
from data_models import FileManifestEntry, WorkspaceSnapshot


@dataclass
class WorkspaceManagerConfig:
    """Workspace manager configuration."""

    root_dir: str = "/tmp/rd_agent_workspaces"


class WorkspaceManager:
    """Manages workspace lifecycle and checkpoint recovery."""

    def __init__(
        self,
        config: WorkspaceManagerConfig,
        checkpoint_store: Optional[FileCheckpointStore] = None,
    ) -> None:
        self._config = config
        self._root = Path(config.root_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        self._checkpoint_store = checkpoint_store or FileCheckpointStore(CheckpointStoreConfig())

    def _workspace_dir(self, run_id: str, workspace_id: str) -> Path:
        safe_run_id = validate_path_component(run_id, "run_id")
        safe_workspace_id = validate_path_component(workspace_id, "workspace_id")
        path = ensure_within_root(
            self._root,
            self._root / safe_run_id / safe_workspace_id,
            "workspace_id",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _resolve_workspace_path(self, workspace_path: str) -> Path:
        return ensure_within_root(self._root, Path(workspace_path), "workspace_path")

    def create_workspace(
        self, run_id: str, workspace_id: str, source_path: Optional[str] = None
    ) -> str:
        workspace_dir = self._workspace_dir(run_id, workspace_id)
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
        if source_path:
            shutil.copytree(source_path, workspace_dir)
        else:
            workspace_dir.mkdir(parents=True, exist_ok=True)
        return str(workspace_dir)

    def copy_workspace(self, source_workspace: str, run_id: str, workspace_id: str) -> str:
        return self.create_workspace(run_id=run_id, workspace_id=workspace_id, source_path=source_workspace)

    def inject_files(self, workspace_path: str, files: Dict[str, Union[str, bytes]]) -> List[str]:
        workspace_dir = self._resolve_workspace_path(workspace_path)
        written: List[str] = []
        for relative_path, content in files.items():
            target = resolve_relative_to_root(workspace_dir, relative_path, "relative_path")
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")
            written.append(str(target))
        return written

    def create_checkpoint(self, run_id: str, workspace_path: str, checkpoint_id: str) -> WorkspaceSnapshot:
        validate_path_component(run_id, "run_id")
        validate_path_component(checkpoint_id, "checkpoint_id")
        workspace_dir = self._resolve_workspace_path(workspace_path)
        archive_bytes = self._zip_workspace(workspace_dir)
        self._checkpoint_store.save_checkpoint(run_id=run_id, checkpoint_id=checkpoint_id, payload=archive_bytes)
        manifest = self._build_manifest(workspace_dir)
        return WorkspaceSnapshot(
            workspace_id=checkpoint_id,
            run_id=run_id,
            file_manifest=manifest,
            checkpoint_type="zip",
        )

    def restore_checkpoint(self, run_id: str, checkpoint_id: str, workspace_path: str) -> WorkspaceSnapshot:
        validate_path_component(run_id, "run_id")
        validate_path_component(checkpoint_id, "checkpoint_id")
        workspace_dir = self._resolve_workspace_path(workspace_path)
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        payload = self._checkpoint_store.load_checkpoint(run_id=run_id, checkpoint_id=checkpoint_id)
        self._unzip_workspace(payload, workspace_dir)
        manifest = self._build_manifest(workspace_dir)
        return WorkspaceSnapshot(
            workspace_id=checkpoint_id,
            run_id=run_id,
            file_manifest=manifest,
            checkpoint_type="zip",
        )

    def execute_with_recovery(
        self,
        run_id: str,
        checkpoint_id: str,
        workspace_path: str,
        operation: Callable[[Path], None],
    ) -> bool:
        """Run operation and auto-restore workspace on exception."""

        validate_path_component(run_id, "run_id")
        validate_path_component(checkpoint_id, "checkpoint_id")
        workspace_dir = self._resolve_workspace_path(workspace_path)
        try:
            operation(workspace_dir)
            return True
        except Exception:
            self.restore_checkpoint(run_id=run_id, checkpoint_id=checkpoint_id, workspace_path=workspace_path)
            return False

    def _zip_workspace(self, workspace_dir: Path) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for path in workspace_dir.rglob("*"):
                if path.is_file():
                    zip_file.write(path, arcname=str(path.relative_to(workspace_dir)))
        return buffer.getvalue()

    def _unzip_workspace(self, payload: bytes, workspace_dir: Path) -> None:
        with zipfile.ZipFile(io.BytesIO(payload), mode="r") as zip_file:
            for member in zip_file.infolist():
                if not member.filename:
                    raise ValueError("zip member filename must not be empty")
                target = resolve_relative_to_root(workspace_dir, member.filename, "zip_member")
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zip_file.open(member, "r") as source:
                    target.write_bytes(source.read())

    def _build_manifest(self, workspace_dir: Path) -> List[FileManifestEntry]:
        manifest: List[FileManifestEntry] = []
        for path in sorted(workspace_dir.rglob("*")):
            if not path.is_file():
                continue
            manifest.append(
                FileManifestEntry(
                    path=str(path.relative_to(workspace_dir)),
                    sha256=self._sha256(path),
                )
            )
        return manifest

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(8192)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
