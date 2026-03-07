"""FC-3 4-stage scientific reasoning pipeline per RDAgent paper Appendix E.3."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from llm.adapter import LLMAdapter
from llm.prompts import (
    reasoning_analysis_prompt,
    reasoning_design_prompt,
    reasoning_hypothesize_prompt,
    reasoning_identify_prompt,
)
from llm.schemas import (
    AnalysisResult,
    ExperimentDesign,
    HypothesisFormulation,
    ProblemIdentification,
)
from service_contracts import ModelSelectorConfig

_log = logging.getLogger(__name__)


class ReasoningPipeline:
    """4-stage scientific reasoning: analyze -> identify -> hypothesize -> design.

    Paper reference: Appendix E.3 - stages 1-3 could share one LLM call,
    stage 4 is separate. We implement 4 separate calls for testability.
    Future optimization: combine stages 1-3 into one call if latency matters.
    """

    def __init__(self, llm_adapter: LLMAdapter) -> None:
        self._llm_adapter = llm_adapter

    def reason(
        self,
        task_summary: str,
        scenario_name: str,
        iteration: int,
        previous_results: List[str],
        current_scores: List[float],
        model_config: Optional[ModelSelectorConfig] = None,
    ) -> ExperimentDesign:
        """Run 4-stage reasoning pipeline, return experiment design."""

        analysis = self._stage_analysis(
            task_summary,
            scenario_name,
            iteration,
            previous_results,
            current_scores,
            model_config,
        )

        problem = self._stage_identify(
            analysis,
            task_summary,
            scenario_name,
            model_config,
        )

        hypothesis = self._stage_hypothesize(
            analysis,
            problem,
            task_summary,
            scenario_name,
            model_config,
        )

        design = self._stage_design(
            analysis,
            problem,
            hypothesis,
            task_summary,
            scenario_name,
            iteration,
            model_config,
        )

        _log.info(
            "Reasoning pipeline complete: %s",
            design.summary[:80] if design.summary else "(empty)",
        )
        return design

    def _stage_analysis(
        self,
        task_summary: str,
        scenario_name: str,
        iteration: int,
        previous_results: List[str],
        current_scores: List[float],
        model_config: Optional[ModelSelectorConfig],
    ) -> AnalysisResult:
        prompt = reasoning_analysis_prompt(
            task_summary=task_summary,
            scenario_name=scenario_name,
            iteration=iteration,
            previous_results=previous_results,
            current_scores=current_scores,
        )
        return self._llm_adapter.generate_structured(
            prompt,
            AnalysisResult,
            model_config=model_config,
        )

    def _stage_identify(
        self,
        analysis: AnalysisResult,
        task_summary: str,
        scenario_name: str,
        model_config: Optional[ModelSelectorConfig],
    ) -> ProblemIdentification:
        prompt = reasoning_identify_prompt(
            analysis_text=analysis.key_observations,
            task_summary=task_summary,
            scenario_name=scenario_name,
        )
        return self._llm_adapter.generate_structured(
            prompt,
            ProblemIdentification,
            model_config=model_config,
        )

    def _stage_hypothesize(
        self,
        analysis: AnalysisResult,
        problem: ProblemIdentification,
        task_summary: str,
        scenario_name: str,
        model_config: Optional[ModelSelectorConfig],
    ) -> HypothesisFormulation:
        prompt = reasoning_hypothesize_prompt(
            analysis_text=analysis.key_observations,
            problem_text=problem.problem,
            task_summary=task_summary,
            scenario_name=scenario_name,
        )
        return self._llm_adapter.generate_structured(
            prompt,
            HypothesisFormulation,
            model_config=model_config,
        )

    def _stage_design(
        self,
        analysis: AnalysisResult,
        problem: ProblemIdentification,
        hypothesis: HypothesisFormulation,
        task_summary: str,
        scenario_name: str,
        iteration: int,
        model_config: Optional[ModelSelectorConfig],
    ) -> ExperimentDesign:
        prompt = reasoning_design_prompt(
            analysis_text=analysis.key_observations,
            problem_text=problem.problem,
            hypothesis_text=hypothesis.hypothesis,
            task_summary=task_summary,
            scenario_name=scenario_name,
            iteration=iteration,
        )
        prompt = prompt.replace("`virtual_score`", "virtual_score")
        return self._llm_adapter.generate_structured(
            prompt,
            ExperimentDesign,
            model_config=model_config,
        )

    def _build_reasoning_trace(
        self,
        analysis: AnalysisResult,
        problem: ProblemIdentification,
        hypothesis: HypothesisFormulation,
        design: ExperimentDesign,
    ) -> Dict[str, Any]:
        """Build trace dict for logging/storage of 4-stage output."""
        return {
            "analysis": {
                "strengths": analysis.strengths,
                "weaknesses": analysis.weaknesses,
                "current_performance": analysis.current_performance,
                "key_observations": analysis.key_observations,
            },
            "problem": {
                "problem": problem.problem,
                "severity": problem.severity,
                "evidence": problem.evidence,
                "affected_component": problem.affected_component,
            },
            "hypothesis": {
                "hypothesis": hypothesis.hypothesis,
                "mechanism": hypothesis.mechanism,
                "expected_improvement": hypothesis.expected_improvement,
                "testable_prediction": hypothesis.testable_prediction,
            },
            "design": {
                "summary": design.summary,
                "constraints": design.constraints,
                "virtual_score": design.virtual_score,
                "implementation_steps": design.implementation_steps,
            },
        }
