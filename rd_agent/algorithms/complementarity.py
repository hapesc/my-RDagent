"""Phase 27 complementarity algorithms for merge-stage parent selection."""

from __future__ import annotations

import math
from collections.abc import Mapping

from rd_agent.contracts.exploration import ComponentClass


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity with zero-vector guard."""

    if len(vec_a) != len(vec_b):
        raise ValueError("vectors must have same length")
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def component_coverage_distance(
    branch_a_components: Mapping[str | ComponentClass, float],
    branch_b_components: Mapping[str | ComponentClass, float],
    *,
    strength_threshold: float = 0.7,
) -> float:
    """Fraction of component classes where strength coverage is complementary."""

    normalized_a = _normalize_component_scores(branch_a_components)
    normalized_b = _normalize_component_scores(branch_b_components)
    all_classes = set(normalized_a) | set(normalized_b)
    if not all_classes:
        return 0.0

    complementary = 0
    for component_class in all_classes:
        a_score = normalized_a.get(component_class, 0.0)
        b_score = normalized_b.get(component_class, 0.0)
        if (a_score >= strength_threshold) != (b_score >= strength_threshold):
            complementary += 1
    return complementary / len(all_classes)


def complementarity_score(
    coverage_dist: float,
    semantic_dist: float,
    *,
    w_coverage: float = 0.6,
    w_semantic: float = 0.4,
) -> float:
    """Weighted combination of coverage and semantic complementarity."""

    return w_coverage * coverage_dist + w_semantic * semantic_dist


def _normalize_component_scores(
    component_scores: Mapping[str | ComponentClass, float],
) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for component_key, score in component_scores.items():
        key = component_key.value if isinstance(component_key, ComponentClass) else component_key
        normalized[key] = score
    return normalized


__all__ = [
    "complementarity_score",
    "component_coverage_distance",
    "cosine_similarity",
]
