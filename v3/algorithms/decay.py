"""Shared Phase 26 decay and diversity helpers."""

from __future__ import annotations

import math


def cosine_decay(budget_ratio: float, *, high: float = 0.7, low: float = 0.3) -> float:
    """Smoothly decay from `high` to `low` over the closed interval [0, 1]."""

    clamped = min(1.0, max(0.0, budget_ratio))
    return low + 0.5 * (high - low) * (1.0 + math.cos(math.pi * clamped))


def category_entropy(category_counts: dict[str, int]) -> float:
    """Return Shannon entropy over category counts."""

    total = sum(max(count, 0) for count in category_counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in category_counts.values():
        if count <= 0:
            continue
        proportion = count / total
        entropy -= proportion * math.log2(proportion)
    return entropy


__all__ = ["category_entropy", "cosine_decay"]
