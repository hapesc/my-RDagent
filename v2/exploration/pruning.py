from __future__ import annotations

from v2.exploration.scheduler import BranchInfo


class BranchPruner:
    def prune(self, dag: dict[str, BranchInfo], threshold: float = 0.1) -> None:
        for info in dag.values():
            if info.score < threshold:
                info.status = "pruned"


__all__ = ["BranchPruner"]
