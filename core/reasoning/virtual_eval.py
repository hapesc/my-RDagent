"""FC-3 virtual evaluation: generate N candidates, rank top K."""
from __future__ import annotations

import logging
from typing import List, Optional

from core.reasoning.pipeline import ReasoningPipeline
from llm.adapter import LLMAdapter
from llm.prompts import virtual_eval_prompt
from llm.schemas import ExperimentDesign, VirtualEvalResult
from service_contracts import ModelSelectorConfig

_log = logging.getLogger(__name__)


class VirtualEvaluator:
    def __init__(
        self,
        llm_adapter: LLMAdapter,
        n_candidates: int = 5,
        k_forward: int = 2,
        reasoning_pipeline: Optional[ReasoningPipeline] = None,
    ) -> None:
        self._llm_adapter = llm_adapter
        self._pipeline = reasoning_pipeline or ReasoningPipeline(llm_adapter)
        self._n_candidates = n_candidates
        self._k_forward = k_forward

    def evaluate(
        self,
        task_summary: str,
        scenario_name: str,
        iteration: int,
        previous_results: List[str],
        current_scores: List[float],
        evaluation_criteria: str = "feasibility, novelty, expected performance gain",
        model_config: Optional[ModelSelectorConfig] = None,
        n_candidates: Optional[int] = None,
        k_forward: Optional[int] = None,
    ) -> List[ExperimentDesign]:
        effective_n_candidates = n_candidates if n_candidates is not None else self._n_candidates
        effective_k_forward = k_forward if k_forward is not None else self._k_forward
        effective_n_candidates = max(1, int(effective_n_candidates))
        effective_k_forward = max(1, min(int(effective_k_forward), effective_n_candidates))

        candidates: List[ExperimentDesign] = []
        for i in range(effective_n_candidates):
            diversified_task = self._diversify_prompt(task_summary, i, effective_n_candidates)
            design = self._pipeline.reason(
                task_summary=diversified_task,
                scenario_name=scenario_name,
                iteration=iteration,
                previous_results=previous_results,
                current_scores=current_scores,
                model_config=model_config,
            )
            candidates.append(design)
            _log.debug(
                "Generated candidate %d/%d: %s",
                i + 1,
                effective_n_candidates,
                design.summary[:50],
            )

        if effective_n_candidates <= effective_k_forward:
            _log.debug(
                "N=%d <= K=%d, returning all candidates",
                effective_n_candidates,
                effective_k_forward,
            )
            return candidates

        candidate_dicts = [
            {"index": i, "summary": d.summary, "virtual_score": d.virtual_score}
            for i, d in enumerate(candidates)
        ]
        ranking_prompt = virtual_eval_prompt(
            candidates=candidate_dicts,
            task_summary=task_summary,
            scenario_name=scenario_name,
            evaluation_criteria=evaluation_criteria,
        )
        eval_result = self._llm_adapter.generate_structured(
            ranking_prompt,
            VirtualEvalResult,
            model_config=model_config,
        )
        _log.debug(
            "Ranking result: %s, selected: %s",
            eval_result.rankings,
            eval_result.selected_indices,
        )

        selected_indices = eval_result.selected_indices[:effective_k_forward]
        valid_indices = [i for i in selected_indices if 0 <= i < len(candidates)]

        if len(valid_indices) < effective_k_forward and eval_result.rankings:
            valid_from_rankings = [i for i in eval_result.rankings if 0 <= i < len(candidates)]
            valid_indices = valid_from_rankings[:effective_k_forward]

        if not valid_indices:
            valid_indices = list(range(min(effective_k_forward, len(candidates))))

        return [candidates[i] for i in valid_indices]

    @staticmethod
    def _diversify_prompt(base_task: str, candidate_index: int, n_total: int) -> str:
        if candidate_index == 0:
            return base_task
        return (
            f"{base_task}\n\n"
            f"[Diversity hint: This is candidate {candidate_index + 1} of {n_total}. "
            f"Explore a DIFFERENT approach from previous candidates. "
            f"Consider alternative methods, different features, or novel techniques.]"
        )
