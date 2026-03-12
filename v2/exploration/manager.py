from __future__ import annotations

from v2.exploration.pruning import BranchPruner
from v2.exploration.scheduler import BranchInfo, DAGScheduler


class V2ExplorationManager:
    def __init__(self, scheduler: DAGScheduler | None = None, pruner: BranchPruner | None = None) -> None:
        self._scheduler = scheduler or DAGScheduler()
        self._pruner = pruner or BranchPruner()

    def expand(self, parent_ids: list[str]) -> str:
        return self._scheduler.add_branch(parent_ids=parent_ids)

    def register_result(self, branch_id: str, reward: float) -> None:
        self._scheduler.register_result(branch_id=branch_id, reward=reward)

    def select_next_branch(self) -> str | None:
        return self._scheduler.select_next_branch()

    def prune(self, threshold: float = 0.1) -> None:
        self._pruner.prune(self._scheduler._dag, threshold=threshold)

    def get_branch_info(self, branch_id: str) -> BranchInfo:
        return self._scheduler.get_branch_info(branch_id)

    def get_active_branches(self) -> list[BranchInfo]:
        return self._scheduler.get_active_branches()


__all__ = ["V2ExplorationManager"]
