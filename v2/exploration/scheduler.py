from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BranchInfo:
    branch_id: str
    parent_ids: list[str] = field(default_factory=list)
    score: float = 0.5
    status: str = "pending"


class DAGScheduler:
    def __init__(self) -> None:
        self._dag: dict[str, BranchInfo] = {}
        self._branch_index: int = 0

    def add_branch(self, parent_ids: list[str]) -> str:
        branch_id = f"b{self._branch_index}"
        self._branch_index += 1

        score = self._initial_score(parent_ids)
        self._dag[branch_id] = BranchInfo(
            branch_id=branch_id, parent_ids=list(parent_ids), score=score, status="pending"
        )
        return branch_id

    def register_result(self, branch_id: str, reward: float) -> None:
        info = self._require_branch(branch_id)
        info.score = reward
        info.status = "completed"

    def select_next_branch(self) -> str | None:
        eligible = [
            info
            for info in self._dag.values()
            if info.status == "pending" and all(self._is_parent_completed(parent_id) for parent_id in info.parent_ids)
        ]
        if not eligible:
            return None
        eligible.sort(key=lambda item: (-item.score, item.branch_id))
        return eligible[0].branch_id

    def get_branch_info(self, branch_id: str) -> BranchInfo:
        return self._require_branch(branch_id)

    def get_active_branches(self) -> list[BranchInfo]:
        return [info for info in self._dag.values() if info.status != "pruned"]

    def _initial_score(self, parent_ids: list[str]) -> float:
        if not parent_ids:
            return 0.5
        parent_scores = [self._require_branch(parent_id).score for parent_id in parent_ids]
        return sum(parent_scores) / len(parent_scores)

    def _is_parent_completed(self, parent_id: str) -> bool:
        parent = self._require_branch(parent_id)
        return parent.status == "completed"

    def _require_branch(self, branch_id: str) -> BranchInfo:
        if branch_id not in self._dag:
            raise KeyError(f"Unknown branch_id: {branch_id}")
        return self._dag[branch_id]


__all__ = ["BranchInfo", "DAGScheduler"]
