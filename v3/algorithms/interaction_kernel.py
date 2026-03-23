"""Phase 27 interaction-kernel math and sampling helpers."""

from __future__ import annotations

import math
import random


def compute_interaction_potential(
    similarity: float,
    score_delta: float,
    depth: int,
    *,
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.1,
) -> float:
    """Compute pairwise interaction potential between two branches."""

    time_decay = math.exp(-gamma * depth)
    return alpha * similarity * time_decay + beta * math.tanh(score_delta)


def softmax_weights(potentials: list[float]) -> list[float]:
    """Normalize interaction potentials with a numerically stable softmax."""

    if not potentials:
        return []

    max_u = max(potentials)
    exponentials = [math.exp(potential - max_u) for potential in potentials]
    denominator = sum(exponentials)
    if denominator == 0.0:
        return [1.0 / len(potentials)] * len(potentials)
    return [value / denominator for value in exponentials]


def sample_branches(potentials: list[float], branch_ids: list[str], k: int) -> list[str]:
    """Sample branch ids categorically from interaction potentials."""

    weights = softmax_weights(potentials)
    selected = random.choices(branch_ids, weights=weights, k=k)
    return list(dict.fromkeys(selected))


def dynamic_sample_count(budget_ratio: float) -> int:
    """Adapt sample count to the exploration/convergence budget stage."""

    if budget_ratio < 0.3:
        return 3
    if budget_ratio < 0.8:
        return 1
    return 2


__all__ = [
    "compute_interaction_potential",
    "dynamic_sample_count",
    "sample_branches",
    "softmax_weights",
]
