from __future__ import annotations

from v3.algorithms.prune import prune_branch_candidates


def test_signal4_exempts_branch_with_unique_components() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.95), ("novel", 0.20), ("duplicate", 0.25)],
        relative_threshold=0.5,
        branch_component_classes={
            "best": {"model"},
            "novel": {"ensemble"},
            "duplicate": {"model"},
        },
        global_best_component_classes={"model"},
    )

    assert pruned == ["duplicate"]


def test_signal4_still_prunes_branch_without_unique_components() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.95), ("duplicate", 0.20)],
        relative_threshold=0.5,
        branch_component_classes={
            "best": {"model", "ensemble"},
            "duplicate": {"model"},
        },
        global_best_component_classes={"model", "ensemble"},
    )

    assert pruned == ["duplicate"]


def test_signal4_is_skipped_when_component_data_is_missing() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.95), ("candidate", 0.20)],
        relative_threshold=0.5,
        branch_component_classes=None,
        global_best_component_classes={"model"},
    )

    assert pruned == ["candidate"]


def test_signal4_still_respects_min_active_branches() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.95), ("novel", 0.20), ("candidate", 0.10)],
        relative_threshold=0.5,
        min_active_branches=3,
        branch_component_classes={
            "best": {"model"},
            "novel": {"ensemble"},
            "candidate": {"model"},
        },
        global_best_component_classes={"model"},
    )

    assert pruned == []


def test_existing_three_signal_behavior_is_unchanged_without_component_data() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.90), ("protected", 0.50), ("overfit", 0.40)],
        budget_ratio=1.0,
        generalization_gaps={"protected": 0.05, "overfit": 0.20},
        overfitting_risks={"protected": 0.10, "overfit": 0.80},
    )

    assert pruned == ["overfit"]
