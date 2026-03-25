from __future__ import annotations

import pytest

from v3.algorithms.complementarity import cosine_similarity
from v3.ports.holdout_port import FoldSpec


@pytest.fixture
def fold() -> FoldSpec:
    return FoldSpec(
        fold_index=0,
        train_ref="run-1-default-train-0",
        holdout_ref="run-1-default-holdout-0",
    )


def test_default_holdout_split_port_returns_k_fold_specs() -> None:
    from v3.ports.defaults import DefaultHoldoutSplitPort

    folds = DefaultHoldoutSplitPort(k=5, seed=42).split(run_id="run-1")

    assert len(folds) == 5
    assert all(isinstance(fold, FoldSpec) for fold in folds)


def test_default_holdout_split_port_populates_fold_fields() -> None:
    from v3.ports.defaults import DefaultHoldoutSplitPort

    folds = DefaultHoldoutSplitPort(k=5, seed=42).split(run_id="run-1")

    assert {fold.fold_index for fold in folds} == set(range(5))
    assert all(fold.train_ref for fold in folds)
    assert all(fold.holdout_ref for fold in folds)


def test_default_holdout_split_port_is_deterministic_for_same_seed() -> None:
    from v3.ports.defaults import DefaultHoldoutSplitPort

    port = DefaultHoldoutSplitPort(k=5, seed=42)

    assert port.split(run_id="run-1") == port.split(run_id="run-1")


def test_default_holdout_split_port_changes_order_for_different_seeds() -> None:
    from v3.ports.defaults import DefaultHoldoutSplitPort

    folds_a = DefaultHoldoutSplitPort(k=5, seed=42).split(run_id="run-1")
    folds_b = DefaultHoldoutSplitPort(k=5, seed=43).split(run_id="run-1")

    assert [fold.fold_index for fold in folds_a] != [fold.fold_index for fold in folds_b]


def test_default_evaluation_port_delegates_to_eval_fn(fold: FoldSpec) -> None:
    from v3.ports.defaults import DefaultEvaluationPort

    port = DefaultEvaluationPort(eval_fn=lambda **kw: 0.85, dataset_ref="ds")

    assert port.evaluate(candidate_node_id="n1", fold=fold) == 0.85


def test_default_evaluation_port_propagates_eval_fn_errors(fold: FoldSpec) -> None:
    from v3.ports.defaults import DefaultEvaluationPort

    def _raise(**_: object) -> float:
        raise RuntimeError("boom")

    port = DefaultEvaluationPort(eval_fn=_raise, dataset_ref="ds")

    with pytest.raises(RuntimeError, match="boom"):
        port.evaluate(candidate_node_id="n1", fold=fold)


def test_default_embedding_port_returns_same_dimension_vectors() -> None:
    from v3.ports.defaults import DefaultEmbeddingPort

    vectors = DefaultEmbeddingPort().embed(["hello", "world"])

    assert len(vectors) == 2
    assert len(vectors[0]) == len(vectors[1])


def test_default_embedding_port_vectors_are_not_all_zero() -> None:
    from v3.ports.defaults import DefaultEmbeddingPort

    vectors = DefaultEmbeddingPort().embed(["hello", "world"])

    assert any(value != 0.0 for vector in vectors for value in vector)


def test_default_embedding_port_returns_identical_vectors_for_identical_inputs() -> None:
    from v3.ports.defaults import DefaultEmbeddingPort

    vectors = DefaultEmbeddingPort().embed(["same text", "same text"])

    assert vectors[0] == vectors[1]


def test_default_embedding_port_returns_different_vectors_for_different_inputs() -> None:
    from v3.ports.defaults import DefaultEmbeddingPort

    vectors = DefaultEmbeddingPort().embed(["same text", "different words"])

    assert vectors[0] != vectors[1]


def test_default_embedding_port_similarity_is_higher_for_similar_texts() -> None:
    from v3.ports.defaults import DefaultEmbeddingPort

    vectors = DefaultEmbeddingPort().embed(
        [
            "train gradient boosting model with cross validation",
            "cross validation for gradient boosting model",
            "bake sourdough bread with olive oil",
        ]
    )

    similar = cosine_similarity(vectors[0], vectors[1])
    dissimilar = cosine_similarity(vectors[0], vectors[2])

    assert similar > dissimilar
