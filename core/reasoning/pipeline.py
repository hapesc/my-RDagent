"""FC-3 4-stage scientific reasoning pipeline per RDAgent paper Appendix E.3."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

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
    ReasoningTrace,
)
from service_contracts import ModelSelectorConfig

_log = logging.getLogger(__name__)


class ReasoningPipeline:
    """4-stage scientific reasoning: analyze -> identify -> hypothesize -> design.

    Paper reference: Appendix E.3 - stages 1-3 could share one LLM call,
    stage 4 is separate. We implement 4 separate calls for testability.
    Future optimization: combine stages 1-3 into one call if latency matters.
    """

    def __init__(self, llm_adapter: LLMAdapter, trace_store=None) -> None:
        self._llm_adapter = llm_adapter
        self._trace_store = trace_store

    def reason(
        self,
        task_summary: str,
        scenario_name: str,
        iteration: int,
        previous_results: list[str],
        current_scores: list[float],
        model_config: ModelSelectorConfig | None = None,
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

        trace_dict = self._build_reasoning_trace(analysis, problem, hypothesis, design)
        trace_record = ReasoningTrace(
            trace_id=str(uuid.uuid4()),
            stages=trace_dict,
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "task_summary": task_summary,
                "scenario": scenario_name,
                "iteration": str(iteration),
            },
        )
        if self._trace_store is not None:
            self._trace_store.store(trace_record)

        return design

    def _stage_analysis(
        self,
        task_summary: str,
        scenario_name: str,
        iteration: int,
        previous_results: list[str],
        current_scores: list[float],
        model_config: ModelSelectorConfig | None,
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
        model_config: ModelSelectorConfig | None,
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
        model_config: ModelSelectorConfig | None,
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
        model_config: ModelSelectorConfig | None,
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
    ) -> dict[str, Any]:
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
