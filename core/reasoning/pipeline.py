"""FC-3 4-stage scientific reasoning pipeline per RDAgent paper Appendix E."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

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

    Design decision: We use 4 separate LLM calls (one per stage) for maximum
    testability and debuggability. The paper suggests stages 1-3 could be
    combined into 1-2 calls for latency optimization - this can be done later
    without changing the external interface.
    """

    def __init__(self, llm_adapter: LLMAdapter) -> None:
        self._llm_adapter = llm_adapter

    @staticmethod
    def _experiment_design_prompt(
        analysis_text: str,
        problem_text: str,
        hypothesis_text: str,
        task_summary: str,
        scenario_name: str,
        iteration: int,
    ) -> str:
        prompt = reasoning_design_prompt(
            analysis_text=analysis_text,
            problem_text=problem_text,
            hypothesis_text=hypothesis_text,
            task_summary=task_summary,
            scenario_name=scenario_name,
            iteration=iteration,
        )
        return prompt.replace("`virtual_score`", "virtual_score")

    def reason(
        self,
        task_summary: str,
        scenario_name: str,
        iteration: int,
        previous_results: List[str],
        current_scores: List[float],
        model_config: Optional[ModelSelectorConfig] = None,
    ) -> ExperimentDesign:
        """Run 4-stage reasoning pipeline and return experiment design."""
        analysis = self._llm_adapter.generate_structured(
            reasoning_analysis_prompt(
                task_summary=task_summary,
                scenario_name=scenario_name,
                iteration=iteration,
                previous_results=previous_results,
                current_scores=current_scores,
            ),
            AnalysisResult,
            model_config=model_config,
        )
        _log.debug("Stage 1 analysis: %s", analysis.key_observations)

        problem = self._llm_adapter.generate_structured(
            reasoning_identify_prompt(
                analysis_text=analysis.key_observations,
                task_summary=task_summary,
                scenario_name=scenario_name,
            ),
            ProblemIdentification,
            model_config=model_config,
        )
        _log.debug("Stage 2 problem: %s", problem.problem)

        hypothesis = self._llm_adapter.generate_structured(
            reasoning_hypothesize_prompt(
                analysis_text=analysis.key_observations,
                problem_text=problem.problem,
                task_summary=task_summary,
                scenario_name=scenario_name,
            ),
            HypothesisFormulation,
            model_config=model_config,
        )
        _log.debug("Stage 3 hypothesis: %s", hypothesis.hypothesis)

        design = self._llm_adapter.generate_structured(
            self._experiment_design_prompt(
                analysis_text=analysis.key_observations,
                problem_text=problem.problem,
                hypothesis_text=hypothesis.hypothesis,
                task_summary=task_summary,
                scenario_name=scenario_name,
                iteration=iteration,
            ),
            ExperimentDesign,
            model_config=model_config,
        )
        _log.debug("Stage 4 design: %s", design.summary)

        return design

    def reason_with_trace(
        self,
        task_summary: str,
        scenario_name: str,
        iteration: int,
        previous_results: List[str],
        current_scores: List[float],
        model_config: Optional[ModelSelectorConfig] = None,
    ) -> Tuple[ExperimentDesign, Dict[str, Any]]:
        """Run pipeline and return (design, trace_dict) for debugging/storage.

        Returns:
            Tuple of (ExperimentDesign, Dict with keys: analysis, problem, hypothesis, design)
        """
        analysis = self._llm_adapter.generate_structured(
            reasoning_analysis_prompt(
                task_summary=task_summary,
                scenario_name=scenario_name,
                iteration=iteration,
                previous_results=previous_results,
                current_scores=current_scores,
            ),
            AnalysisResult,
            model_config=model_config,
        )
        problem = self._llm_adapter.generate_structured(
            reasoning_identify_prompt(
                analysis_text=analysis.key_observations,
                task_summary=task_summary,
                scenario_name=scenario_name,
            ),
            ProblemIdentification,
            model_config=model_config,
        )
        hypothesis = self._llm_adapter.generate_structured(
            reasoning_hypothesize_prompt(
                analysis_text=analysis.key_observations,
                problem_text=problem.problem,
                task_summary=task_summary,
                scenario_name=scenario_name,
            ),
            HypothesisFormulation,
            model_config=model_config,
        )
        design = self._llm_adapter.generate_structured(
            self._experiment_design_prompt(
                analysis_text=analysis.key_observations,
                problem_text=problem.problem,
                hypothesis_text=hypothesis.hypothesis,
                task_summary=task_summary,
                scenario_name=scenario_name,
                iteration=iteration,
            ),
            ExperimentDesign,
            model_config=model_config,
        )
        trace = self._build_reasoning_trace(analysis, problem, hypothesis, design)
        return design, trace

    @staticmethod
    def _build_reasoning_trace(
        analysis: AnalysisResult,
        problem: ProblemIdentification,
        hypothesis: HypothesisFormulation,
        design: ExperimentDesign,
    ) -> Dict[str, Any]:
        """Assemble all 4 stages into a trace dict for logging/storage."""
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
