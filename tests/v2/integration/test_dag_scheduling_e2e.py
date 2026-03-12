from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from v2.runtime import build_v2_runtime


class TestDAGSchedulingE2E:
    def test_expand_and_select(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock"})
        manager = ctx.exploration_manager

        root = manager.expand(parent_ids=[])
        manager.register_result(root, reward=0.2)

        bonus_parent = manager.expand(parent_ids=[])
        manager.register_result(bonus_parent, reward=0.9)

        child_low = manager.expand(parent_ids=[root])
        child_high = manager.expand(parent_ids=[root, bonus_parent])

        assert manager.get_branch_info(child_low).score == 0.2
        assert manager.get_branch_info(child_high).score == 0.55
        assert manager.select_next_branch() == child_high

    def test_backpropagate_updates_reward(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock"})
        manager = ctx.exploration_manager

        branch_id = manager.expand(parent_ids=[])
        assert manager.get_branch_info(branch_id).score == 0.5

        manager.register_result(branch_id, reward=0.88)
        info = manager.get_branch_info(branch_id)

        assert info.score == 0.88
        assert info.status == "completed"

    def test_prune_low_reward_branch(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock"})
        manager = ctx.exploration_manager

        parent_low = manager.expand(parent_ids=[])
        parent_high = manager.expand(parent_ids=[])
        manager.register_result(parent_low, reward=0.05)
        manager.register_result(parent_high, reward=0.9)

        child_low = manager.expand(parent_ids=[parent_low])
        child_high = manager.expand(parent_ids=[parent_high])

        manager.prune(threshold=0.1)

        assert manager.get_branch_info(child_low).status == "pruned"
        assert manager.get_branch_info(child_high).status == "pending"
        assert manager.select_next_branch() == child_high

    def test_dag_merge_two_parents(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock"})
        manager = ctx.exploration_manager

        parent_a = manager.expand(parent_ids=[])
        parent_b = manager.expand(parent_ids=[])
        manager.register_result(parent_a, reward=0.7)
        manager.register_result(parent_b, reward=0.9)

        merged = manager.expand(parent_ids=[parent_a, parent_b])
        info = manager.get_branch_info(merged)

        assert info.parent_ids == [parent_a, parent_b]
        assert info.score == 0.8

    def test_topological_sort(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock"})
        manager = ctx.exploration_manager

        root = manager.expand(parent_ids=[])
        assert manager.select_next_branch() == root
        manager.register_result(root, reward=0.6)

        child_a = manager.expand(parent_ids=[root])
        grandchild = manager.expand(parent_ids=[child_a])
        child_c = manager.expand(parent_ids=[root])

        selected_order: list[str] = []

        next_branch = manager.select_next_branch()
        assert next_branch is not None
        selected_order.append(next_branch)
        manager.register_result(next_branch, reward=0.6)

        next_branch = manager.select_next_branch()
        assert next_branch is not None
        selected_order.append(next_branch)
        manager.register_result(next_branch, reward=0.6)

        next_branch = manager.select_next_branch()
        assert next_branch is not None
        selected_order.append(next_branch)

        assert selected_order == [child_a, grandchild, child_c]
