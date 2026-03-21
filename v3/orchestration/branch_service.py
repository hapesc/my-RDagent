"""Authoritative branch reads over persisted V3 snapshots."""

from __future__ import annotations

from collections.abc import Callable

from v3.contracts.branch import BranchSnapshot
from v3.ports.state_store import StateStorePort


class BranchService:
    """Loads branch truth from V3-owned snapshots and only backfills on request."""

    def __init__(
        self,
        state_store: StateStorePort,
        *,
        migration_loader: Callable[[str], BranchSnapshot | None] | None = None,
    ) -> None:
        self._state_store = state_store
        self._migration_loader = migration_loader

    def get_branch(self, branch_id: str, *, allow_backfill: bool = False) -> BranchSnapshot | None:
        branch = self._state_store.load_branch_snapshot(branch_id)
        if branch is not None:
            return branch
        if not allow_backfill or self._migration_loader is None:
            return None
        branch = self._migration_loader(branch_id)
        if branch is not None:
            self._state_store.write_branch_snapshot(branch)
        return branch


__all__ = ["BranchService"]
