from __future__ import annotations

from pathlib import Path

from v2.exploration.manager import V2ExplorationManager
from v2.exploration.pruning import BranchPruner
from v2.exploration.scheduler import DAGScheduler


def test_select_next_branch_picks_highest_reward_eligible_branch() -> None:
    manager = V2ExplorationManager(scheduler=DAGScheduler(), pruner=BranchPruner())

    parent_high = manager.expand(parent_ids=[])
    parent_low = manager.expand(parent_ids=[])
    manager.register_result(parent_high, reward=0.8)
    manager.register_result(parent_low, reward=0.3)

    child_high = manager.expand(parent_ids=[parent_high])
    _child_low = manager.expand(parent_ids=[parent_low])

    assert manager.get_branch_info(child_high).score == 0.8
    assert manager.select_next_branch() == child_high


def test_expand_supports_multi_parent_branch() -> None:
    manager = V2ExplorationManager()

    parent_a = manager.expand(parent_ids=[])
    parent_b = manager.expand(parent_ids=[])
    manager.register_result(parent_a, reward=0.7)
    manager.register_result(parent_b, reward=0.9)

    child = manager.expand(parent_ids=[parent_a, parent_b])
    info = manager.get_branch_info(child)

    assert info.parent_ids == [parent_a, parent_b]
    assert info.score == 0.8


def test_prune_marks_low_score_branches_pruned() -> None:
    manager = V2ExplorationManager()

    branch_low = manager.expand(parent_ids=[])
    branch_high = manager.expand(parent_ids=[])
    manager.register_result(branch_low, reward=0.05)
    manager.register_result(branch_high, reward=0.9)

    manager.prune(threshold=0.1)

    assert manager.get_branch_info(branch_low).status == "pruned"
    assert manager.get_branch_info(branch_high).status == "completed"
    active_ids = {branch.branch_id for branch in manager.get_active_branches()}
    assert branch_low not in active_ids
    assert branch_high in active_ids


def test_exploration_module_has_no_banned_search_terms() -> None:
    exploration_dir = Path("v2/exploration")
    banned_terms = ["PUCT", "UCB", "MCTS", "mcts", "puct", "ucb_score"]

    for file_path in exploration_dir.glob("*.py"):
        content = file_path.read_text(encoding="utf-8")
        for term in banned_terms:
            assert term not in content, f"Found banned term {term!r} in {file_path}"
