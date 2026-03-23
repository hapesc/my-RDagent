from __future__ import annotations

import pytest

from v3.algorithms.complementarity import (
    complementarity_score,
    component_coverage_distance,
    cosine_similarity,
)


def test_cosine_similarity_matches_expected_cases() -> None:
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) == pytest.approx(0.0)
    assert cosine_similarity([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]) == pytest.approx(-1.0)
    assert cosine_similarity([0.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(0.0)


def test_component_coverage_distance_captures_swapped_and_shared_strengths() -> None:
    assert component_coverage_distance(
        {"model": 0.9, "feature_eng": 0.3},
        {"model": 0.3, "feature_eng": 0.9},
    ) == pytest.approx(1.0)

    assert component_coverage_distance({"model": 0.9}, {"model": 0.9}) == pytest.approx(0.0)
    assert component_coverage_distance({}, {}) == pytest.approx(0.0)
    assert component_coverage_distance(
        {"model": 0.9, "ensemble": 0.8},
        {"data_load": 0.9},
    ) > 0.0


def test_complementarity_score_supports_custom_and_default_weights() -> None:
    assert complementarity_score(
        coverage_dist=0.8,
        semantic_dist=0.6,
        w_coverage=0.6,
        w_semantic=0.4,
    ) == pytest.approx(0.72)

    assert complementarity_score(coverage_dist=0.5, semantic_dist=0.25) == pytest.approx(0.4)
