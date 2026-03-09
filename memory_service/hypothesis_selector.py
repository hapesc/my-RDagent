from __future__ import annotations

import json

from llm.prompts import hypothesis_modification_prompt
from llm.schemas import HypothesisModification
from memory_service.interaction_kernel import HypothesisRecord, InteractionKernel


class HypothesisSelector:
    def __init__(
        self,
        interaction_kernel: InteractionKernel,
        llm_adapter=None,
    ) -> None:
        self._kernel = interaction_kernel
        self._llm = llm_adapter

    def select_hypothesis(self, candidates: list[HypothesisRecord], context: str) -> HypothesisRecord:
        if not candidates:
            raise ValueError("candidates list must not be empty")
        return max(candidates, key=lambda h: h.score)

    def modify_hypothesis(
        self,
        source: HypothesisRecord,
        context_items: list[str],
        task_summary: str,
        scenario_name: str,
    ) -> HypothesisModification:
        if self._llm is None:
            return HypothesisModification(
                modified_hypothesis=source.text,
                modification_type="identity",
                source_hypothesis=source.text,
                reasoning="No LLM adapter available; returning source unmodified",
            )

        prompt = hypothesis_modification_prompt(
            source_hypothesis=source.text,
            action="modify",
            context_items=context_items,
            task_summary=task_summary,
            scenario_name=scenario_name,
        )
        raw = self._llm.complete(prompt)
        data = json.loads(raw)
        return HypothesisModification.from_dict(data)

    def generate_hypothesis(
        self,
        context_items: list[str],
        task_summary: str,
        scenario_name: str,
    ) -> HypothesisModification:
        if self._llm is None:
            return HypothesisModification(
                modified_hypothesis="",
                modification_type="none",
                source_hypothesis="",
                reasoning="No LLM adapter available; cannot generate",
            )

        prompt = hypothesis_modification_prompt(
            source_hypothesis="(none - generate new)",
            action="generate",
            context_items=context_items,
            task_summary=task_summary,
            scenario_name=scenario_name,
        )
        raw = self._llm.complete(prompt)
        data = json.loads(raw)
        return HypothesisModification.from_dict(data)

    def adaptive_select(
        self,
        candidates: list[HypothesisRecord],
        iteration: int,
        max_iterations: int,
        context_items: list[str],
        task_summary: str,
        scenario_name: str,
    ) -> HypothesisModification:
        progress = 1.0 if max_iterations <= 0 else float(iteration) / float(max_iterations)

        if progress < 0.33:
            return self.generate_hypothesis(context_items, task_summary, scenario_name)
        if progress < 0.66:
            if not candidates:
                return self.generate_hypothesis(context_items, task_summary, scenario_name)
            best = self.select_hypothesis(candidates, "")
            return self.modify_hypothesis(best, context_items, task_summary, scenario_name)

        if not candidates:
            return HypothesisModification(
                modified_hypothesis="",
                modification_type="select",
                source_hypothesis="",
                reasoning="No candidates available for selection",
            )
        best = self.select_hypothesis(candidates, "")
        return HypothesisModification(
            modified_hypothesis=best.text,
            modification_type="select",
            source_hypothesis=best.text,
            reasoning=f"Selected highest-scoring hypothesis (score={best.score})",
        )


def rank_by_kernel(
    target: HypothesisRecord,
    candidates: list[HypothesisRecord],
    kernel: InteractionKernel,
) -> list[tuple[HypothesisRecord, float]]:
    scored = [(c, kernel.compute(target, c)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
