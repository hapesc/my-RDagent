"""Workspace allocation over the canonical Phase 15 branch-isolation contract."""

from __future__ import annotations

import shutil
from pathlib import Path

from v3.orchestration.branch_isolation_service import BranchIsolationService


class BranchWorkspaceManager:
    """Allocates branch-local workspaces using the public isolation contract."""

    def __init__(self, root: str | Path) -> None:
        self._isolation = BranchIsolationService(root)

    def allocate_branch_workspace(self, *, run_id: str, branch_id: str, source_path: str | Path | None = None) -> str:
        workspace_root = self._isolation.workspace_root(run_id, branch_id)
        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        source_root = Path(source_path) if source_path is not None else None
        if source_root is not None and source_root.exists():
            shutil.copytree(source_root, workspace_root)
        else:
            workspace_root.mkdir(parents=True, exist_ok=True)
        return str(workspace_root)

    def workspace_root(self, *, run_id: str, branch_id: str) -> str:
        return str(self._isolation.workspace_root(run_id, branch_id))


__all__ = ["BranchWorkspaceManager"]
