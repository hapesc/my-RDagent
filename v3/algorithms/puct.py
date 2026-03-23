"""Self-contained PUCT selection helpers for V3."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PuctCandidate:
    branch_id: str
    potential: float
    avg_value: float
    visits: int


def select_next_candidate(candidates: list[PuctCandidate], *, c_puct: float = 1.41) -> str | None:
    if not candidates:
        return None

    unvisited = [candidate for candidate in candidates if candidate.visits <= 0]
    if unvisited:
        unscored = [candidate for candidate in unvisited if candidate.potential == 0.0]
        return (unscored[0] if unscored else unvisited[0]).branch_id

    priors = _compute_priors(candidates)
    total_visits = sum(max(candidate.visits, 0) for candidate in candidates)
    sqrt_total = math.sqrt(total_visits)

    best_branch_id: str | None = None
    best_score = float("-inf")
    for candidate in candidates:
        score = candidate.avg_value + c_puct * priors[candidate.branch_id] * sqrt_total / (1 + candidate.visits)
        if score > best_score:
            best_score = score
            best_branch_id = candidate.branch_id
    return best_branch_id


def _compute_priors(candidates: list[PuctCandidate]) -> dict[str, float]:
    potentials = {candidate.branch_id: candidate.potential for candidate in candidates}
    max_potential = max(potentials.values())

    exp_values: dict[str, float] = {}
    exp_sum = 0.0
    for branch_id, potential in potentials.items():
        value = math.exp(potential - max_potential)
        exp_values[branch_id] = value
        exp_sum += value

    if exp_sum == 0.0:
        uniform = 1.0 / len(candidates)
        return {candidate.branch_id: uniform for candidate in candidates}

    return {branch_id: value / exp_sum for branch_id, value in exp_values.items()}
