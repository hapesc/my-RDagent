from __future__ import annotations

from v3.algorithms.prune import prune_branch_candidates


def test_prune_branch_candidates_remains_backward_compatible() -> None:
    assert prune_branch_candidates([("b1", 0.8), ("b2", 0.3)], relative_threshold=0.5) == ["b2"]


def test_prune_branch_candidates_uses_budget_ratio_for_dynamic_threshold() -> None:
    candidates = [("b1", 0.9), ("b2", 0.5), ("b3", 0.2)]

    assert prune_branch_candidates(candidates, budget_ratio=0.0) == ["b3"]
    assert prune_branch_candidates(candidates, budget_ratio=1.0) == ["b2", "b3"]
    assert prune_branch_candidates(candidates, relative_threshold=0.1, budget_ratio=1.0) == ["b2", "b3"]


def test_prune_branch_candidates_protects_generalization_and_prioritizes_overfitting() -> None:
    candidates = [("b1", 0.9), ("b2", 0.5), ("b3", 0.4)]

    protected = prune_branch_candidates(
        candidates,
        budget_ratio=1.0,
        generalization_gaps={"b2": 0.05, "b3": 0.2},
    )
    prioritized = prune_branch_candidates(
        candidates,
        budget_ratio=1.0,
        overfitting_risks={"b2": 0.8, "b3": 0.2},
    )

    assert protected == ["b3"]
    assert prioritized == ["b2", "b3"]


def test_prune_branch_candidates_respects_min_active_branches_and_edge_cases() -> None:
    candidates = [("b1", 0.9), ("b2", 0.5), ("b3", 0.4)]

    assert prune_branch_candidates(candidates, budget_ratio=1.0, min_active_branches=2) == ["b2"]
    assert prune_branch_candidates([], budget_ratio=1.0) == []
    assert prune_branch_candidates([("b1", 0.9)], budget_ratio=1.0) == []
    assert prune_branch_candidates(
        [("b1", 0.8), ("b2", 0.3)],
        relative_threshold=0.5,
        generalization_gaps=None,
        overfitting_risks=None,
    ) == ["b2"]
