"""Shared path validation helpers for workspace and checkpoint isolation."""

from __future__ import annotations

from pathlib import Path, PurePath


def validate_path_component(value: str, label: str) -> str:
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


def ensure_within_root(root: Path, candidate: Path, label: str) -> Path:
    root_resolved = root.resolve(strict=False)
    candidate_resolved = candidate.resolve(strict=False)
    if candidate_resolved != root_resolved and root_resolved not in candidate_resolved.parents:
        raise ValueError(f"{label} escapes configured root")
    return candidate_resolved


def resolve_relative_to_root(root: Path, relative_path: str, label: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"{label} must be relative")
    return ensure_within_root(root, root / candidate, label)
