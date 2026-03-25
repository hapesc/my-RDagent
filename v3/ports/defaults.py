"""Default production-oriented implementations for external dependency ports."""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Callable

from v3.ports.holdout_port import FoldSpec


class DefaultHoldoutSplitPort:
    """Production K-fold splitter with seed-controlled deterministic shuffle."""

    def __init__(self, k: int = 5, seed: int | None = None) -> None:
        self._k = k
        self._seed = seed

    def split(self, *, run_id: str) -> list[FoldSpec]:
        rng = random.Random(self._seed)
        indices = list(range(self._k))
        rng.shuffle(indices)
        return [
            FoldSpec(
                fold_index=index,
                train_ref=f"{run_id}-default-train-{index}",
                holdout_ref=f"{run_id}-default-holdout-{index}",
            )
            for index in indices
        ]


class DefaultEvaluationPort:
    """Parameterized holdout evaluator that delegates to an injected function."""

    def __init__(self, eval_fn: Callable[..., float], dataset_ref: str = "") -> None:
        self._eval_fn = eval_fn
        self._dataset_ref = dataset_ref

    def evaluate(self, *, candidate_node_id: str, fold: FoldSpec) -> float:
        return self._eval_fn(
            candidate_node_id=candidate_node_id,
            fold=fold,
            dataset_ref=self._dataset_ref,
        )


class DefaultEmbeddingPort:
    """Lightweight TF-IDF embedding using only Python stdlib."""

    def __init__(self, dim: int = 256) -> None:
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        tokenized_texts = [self._tokenize(text) for text in texts]
        document_frequency: Counter[str] = Counter()
        for tokens in tokenized_texts:
            for token in set(tokens):
                document_frequency[token] += 1
        document_count = len(texts)
        vectors: list[list[float]] = []
        for tokens in tokenized_texts:
            vector = [0.0] * self._dim
            term_frequency = Counter(tokens)
            for token, count in term_frequency.items():
                tf_value = count / max(len(tokens), 1)
                idf_value = math.log((1 + document_count) / (1 + document_frequency.get(token, 0))) + 1.0
                bucket = hash(token) % self._dim
                vector[bucket] += tf_value * idf_value
            norm = math.sqrt(sum(value * value for value in vector))
            if norm > 0.0:
                vector = [value / norm for value in vector]
            vectors.append(vector)
        return vectors

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return text.lower().split()


__all__ = [
    "DefaultEmbeddingPort",
    "DefaultEvaluationPort",
    "DefaultHoldoutSplitPort",
]
