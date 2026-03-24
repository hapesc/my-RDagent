"""Holdout validation protocol abstractions for Phase 28 aggregated validation."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class FoldSpec(BaseModel):
    """Opaque fold descriptor produced by HoldoutSplitPort."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fold_index: int = Field(ge=0)
    train_ref: str = Field(min_length=1)
    holdout_ref: str = Field(min_length=1)


class HoldoutSplitPort(Protocol):
    """Called once per finalization to produce K fold specs."""

    def split(self, *, run_id: str) -> list[FoldSpec]: ...


class EvaluationPort(Protocol):
    """Called once per candidate per fold to evaluate holdout performance."""

    def evaluate(self, *, candidate_node_id: str, fold: FoldSpec) -> float: ...


class StratifiedKFoldSplitter:
    """Default K-fold splitter producing opaque partition references."""

    def __init__(self, k: int = 5) -> None:
        self._k = k

    def split(self, *, run_id: str) -> list[FoldSpec]:
        return [
            FoldSpec(
                fold_index=index,
                train_ref=f"{run_id}-train-fold-{index}",
                holdout_ref=f"{run_id}-holdout-fold-{index}",
            )
            for index in range(self._k)
        ]


class StubHoldoutSplitPort:
    """Deterministic stub for tests."""

    def __init__(self, k: int = 5) -> None:
        self._k = k

    def split(self, *, run_id: str) -> list[FoldSpec]:
        return [
            FoldSpec(
                fold_index=index,
                train_ref=f"train-fold-{index}",
                holdout_ref=f"holdout-fold-{index}",
            )
            for index in range(self._k)
        ]


class StubEvaluationPort:
    """Returns a fixed score per candidate for deterministic testing."""

    def __init__(self, scores: dict[str, float] | None = None) -> None:
        self._scores = scores or {}

    def evaluate(self, *, candidate_node_id: str, fold: FoldSpec) -> float:
        return self._scores.get(candidate_node_id, 0.5)


__all__ = [
    "EvaluationPort",
    "FoldSpec",
    "HoldoutSplitPort",
    "StratifiedKFoldSplitter",
    "StubEvaluationPort",
    "StubHoldoutSplitPort",
]
