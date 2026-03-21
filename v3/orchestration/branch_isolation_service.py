"""Canonical Phase 15 path construction for branch-local and shared state."""

from __future__ import annotations

from pathlib import Path, PurePath

from v3.contracts.isolation import BranchIsolationSnapshot


class BranchIsolationService:
    """Builds explicit branch-local and shared roots from one vocabulary."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def snapshot(self, *, run_id: str, branch_id: str) -> BranchIsolationSnapshot:
        return BranchIsolationSnapshot(
            run_id=run_id,
            branch_id=branch_id,
            branch_root=str(self.branch_root(branch_id)),
            artifact_root=str(self.artifact_root(run_id, branch_id)),
            memory_root=str(self.memory_root(run_id, branch_id)),
            shared_memory_root=str(self.shared_memory_root(run_id)),
            workspace_root=str(self.workspace_root(run_id, branch_id)),
        )

    def branch_root(self, branch_id: str) -> Path:
        safe_branch_id = _validate_path_component(branch_id, "branch_id")
        return self._resolve(self._root / "branches" / safe_branch_id, "branch_id")

    def artifact_root(self, run_id: str, branch_id: str) -> Path:
        safe_run_id = _validate_path_component(run_id, "run_id")
        safe_branch_id = _validate_path_component(branch_id, "branch_id")
        return self._resolve(self._root / "artifacts" / safe_run_id / safe_branch_id, "branch_id")

    def memory_root(self, run_id: str, branch_id: str) -> Path:
        safe_run_id = _validate_path_component(run_id, "run_id")
        safe_branch_id = _validate_path_component(branch_id, "branch_id")
        return self._resolve(self._root / "memory" / safe_run_id / "branches" / safe_branch_id, "branch_id")

    def shared_memory_root(self, run_id: str) -> Path:
        safe_run_id = _validate_path_component(run_id, "run_id")
        return self._resolve(self._root / "memory" / safe_run_id / "shared", "run_id")

    def workspace_root(self, run_id: str, branch_id: str) -> Path:
        safe_run_id = _validate_path_component(run_id, "run_id")
        safe_branch_id = _validate_path_component(branch_id, "branch_id")
        return self._resolve(
            self._root / "workspaces" / safe_run_id / "branches" / safe_branch_id / "workspace",
            "branch_id",
        )

    def _resolve(self, path: Path, label: str) -> Path:
        return _ensure_within_root(self._root, path, label)


def _validate_path_component(value: str, label: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError(f"{label} must not be empty")
    if candidate in {".", ".."}:
        raise ValueError(f"{label} must not contain relative traversal segments")
    if "/" in candidate or "\\" in candidate:
        raise ValueError(f"{label} must be a single path component")
    pure_path = PurePath(candidate)
    if pure_path.is_absolute() or len(pure_path.parts) != 1:
        raise ValueError(f"{label} must be a single relative path component")
    return candidate


def _ensure_within_root(root: Path, candidate: Path, label: str) -> Path:
    root_resolved = root.resolve(strict=False)
    candidate_resolved = candidate.resolve(strict=False)
    if candidate_resolved != root_resolved and root_resolved not in candidate_resolved.parents:
        raise ValueError(f"{label} escapes configured root")
    return candidate_resolved


__all__ = ["BranchIsolationService"]
