"""Self-contained branch pruning helpers for V3."""

from __future__ import annotations


def prune_branch_candidates(
    candidates: list[tuple[str, float]],
    *,
    score_threshold: float | None = None,
    relative_threshold: float | None = 0.5,
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
    if relative_threshold is not None:
        cutoff = max(cutoff, best_score * relative_threshold)

    pruned: list[str] = []
    for branch_id, score in scored:
        if branch_id in best_ids:
            continue
        if score >= cutoff:
            continue
        remaining = len(candidates) - len(pruned) - 1
        if remaining < 1:
            continue
        pruned.append(branch_id)
    return pruned
