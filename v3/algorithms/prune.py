"""Self-contained branch pruning helpers for V3."""

from __future__ import annotations

from v3.algorithms.decay import cosine_decay


def prune_branch_candidates(
    candidates: list[tuple[str, float]],
    *,
    score_threshold: float | None = None,
    relative_threshold: float | None = 0.5,
    generalization_gaps: dict[str, float] | None = None,
    overfitting_risks: dict[str, float] | None = None,
    budget_ratio: float | None = None,
    min_active_branches: int = 1,
) -> list[str]:
    if len(candidates) <= 1:
        return []

    scored = [(branch_id, score) for branch_id, score in candidates]
    if not scored:
        return []

    best_score = max(score for _, score in scored)
    best_ids = {branch_id for branch_id, score in scored if score == best_score}
    cutoff = float("-inf")
    if score_threshold is not None:
        cutoff = max(cutoff, score_threshold)
    effective_threshold = relative_threshold
    if budget_ratio is not None:
        effective_threshold = cosine_decay(budget_ratio, high=0.3, low=0.7)
    if effective_threshold is not None:
        cutoff = max(cutoff, best_score * effective_threshold)

    prioritized: list[str] = []
    standard: list[str] = []
    for branch_id, score in scored:
        if branch_id in best_ids:
            continue
        if score >= cutoff:
            continue
        if generalization_gaps is not None:
            gap = generalization_gaps.get(branch_id)
            if gap is not None and 0.0 < gap < 0.1:
                continue
        if overfitting_risks is not None and overfitting_risks.get(branch_id, 0.0) > 0.6:
            prioritized.append(branch_id)
        else:
            standard.append(branch_id)

    pruned: list[str] = []
    required_active = max(1, min_active_branches)
    for branch_id in prioritized + standard:
        remaining = len(candidates) - len(pruned) - 1
        if remaining < required_active:
            continue
        pruned.append(branch_id)
    return pruned
