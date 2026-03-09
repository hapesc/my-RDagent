from __future__ import annotations

from typing import TYPE_CHECKING

from data_models import ExecutionResult, Score

if TYPE_CHECKING:
    from .service import EvaluationService


class ValidationSelector:
    def __init__(self, evaluation_service: EvaluationService) -> None:
        self._eval_service = evaluation_service

    def rank_candidates(
        self,
        candidates: list[ExecutionResult],
    ) -> list[tuple[ExecutionResult, Score]]:
        if not candidates:
            return []

        scored: list[tuple[ExecutionResult, Score]] = []
        for candidate in candidates:
            eval_result = self._eval_service.evaluate_run(candidate)
            scored.append((candidate, eval_result.score))

        scored.sort(key=lambda item: item[1].value, reverse=True)
        return scored

    def select_best(
        self,
        candidates: list[ExecutionResult],
    ) -> tuple[ExecutionResult, Score]:
        ranked = self.rank_candidates(candidates)
        if not ranked:
            raise ValueError("No candidates to select from")
        return ranked[0]
