"""Embedding protocol abstractions for Phase 27 interaction kernels."""

from __future__ import annotations

from typing import Protocol


class EmbeddingUnavailableError(Exception):
    """Raised when an embedding service is temporarily unreachable or degraded.

    Consumers may catch this to degrade gracefully (e.g. skip sharing).
    All other exceptions from embed() indicate programming errors and must
    propagate uncaught.
    """


class EmbeddingPort(Protocol):
    """Vectorize a batch of texts into fixed-size embeddings."""

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class StubEmbeddingPort:
    """Deterministic stub used by tests and offline flows."""

    def __init__(self, dim: int = 256) -> None:
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self._dim for _ in texts]


__all__ = ["EmbeddingPort", "EmbeddingUnavailableError", "StubEmbeddingPort"]
