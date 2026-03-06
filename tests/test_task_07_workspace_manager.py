"""Task-07 tests for workspace creation, checkpointing, and recovery."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.execution import WorkspaceManager, WorkspaceManagerConfig
from core.storage import CheckpointStoreConfig, FileCheckpointStore


class WorkspaceManagerTests(unittest.TestCase):
    def test_workspace_create_copy_and_inject(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_root = Path(tmpdir) / "checkpoints"
            workspace_root = Path(tmpdir) / "workspaces"
            manager = WorkspaceManager(
                WorkspaceManagerConfig(root_dir=str(workspace_root)),
                checkpoint_store=FileCheckpointStore(CheckpointStoreConfig(root_dir=str(checkpoint_root))),
            )

            workspace_path = manager.create_workspace(run_id="run-1", workspace_id="ws-1")
            written = manager.inject_files(
                workspace_path,
                {
                    "main.py": "print('hello')",
                    "feature/config.txt": "v1",
                },
            )
            self.assertEqual(len(written), 2)
            self.assertTrue((Path(workspace_path) / "main.py").exists())

            copied_path = manager.copy_workspace(workspace_path, run_id="run-1", workspace_id="ws-2")
            self.assertTrue((Path(copied_path) / "feature/config.txt").exists())

    def test_checkpoint_create_restore_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_root = Path(tmpdir) / "checkpoints"
            workspace_root = Path(tmpdir) / "workspaces"
            manager = WorkspaceManager(
                WorkspaceManagerConfig(root_dir=str(workspace_root)),
                checkpoint_store=FileCheckpointStore(CheckpointStoreConfig(root_dir=str(checkpoint_root))),
            )

            run_id = "run-2"
            workspace_path = manager.create_workspace(run_id=run_id, workspace_id="ws-1")
            manager.inject_files(workspace_path, {"state.txt": "stable"})
            snapshot = manager.create_checkpoint(run_id=run_id, workspace_path=workspace_path, checkpoint_id="cp-1")
            self.assertEqual(snapshot.workspace_id, "cp-1")
            self.assertEqual(len(snapshot.file_manifest), 1)

            def failing_operation(path: Path) -> None:
                (path / "state.txt").write_text("broken", encoding="utf-8")
                raise RuntimeError("simulate failure")

            ok = manager.execute_with_recovery(
                run_id=run_id,
                checkpoint_id="cp-1",
                workspace_path=workspace_path,
                operation=failing_operation,
            )
            self.assertFalse(ok)
            self.assertEqual((Path(workspace_path) / "state.txt").read_text(encoding="utf-8"), "stable")

            manager.inject_files(workspace_path, {"state.txt": "changed"})
            manager.restore_checkpoint(run_id=run_id, checkpoint_id="cp-1", workspace_path=workspace_path)
            self.assertEqual((Path(workspace_path) / "state.txt").read_text(encoding="utf-8"), "stable")


if __name__ == "__main__":
    unittest.main()
