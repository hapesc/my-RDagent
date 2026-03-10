from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from data_models import CodeArtifact, ExperimentNode, FeedbackRecord, Proposal, Score
from plugins.contracts import Coder, FeedbackAnalyzer, Runner, ScenarioContext

if TYPE_CHECKING:
    from llm.schemas import StructuredFeedback

_log = logging.getLogger(__name__)


class CoSTEEREvolver:
    def __init__(
        self,
        coder: Coder,
        runner: Runner,
        feedback_analyzer: FeedbackAnalyzer,
        max_rounds: int = 3,
        llm_adapter=None,
        memory_service=None,
    ) -> None:
        self._coder = coder
        self._runner = runner
        self._feedback_analyzer = feedback_analyzer
        self._max_rounds = max_rounds
        self._llm_adapter = llm_adapter
        self._memory_service = memory_service

    def _analyze_feedback(
        self,
        feedback_record: FeedbackRecord,
        code: str,
        execution_output: str,
    ) -> StructuredFeedback:
        if self._llm_adapter is None:
            raise RuntimeError("Structured feedback requires llm_adapter")

        from llm.prompts import structured_feedback_prompt
        from llm.schemas import StructuredFeedback

        prompt = structured_feedback_prompt(
            code=code,
            execution_output=execution_output,
            task_description=feedback_record.reason,
        )
        return self._llm_adapter.generate_structured(prompt, StructuredFeedback)

    def _get_debug_sample_fraction(self, scenario: ScenarioContext) -> float | None:
        debug_config = scenario.config.get("debug_config")
        if debug_config is None or not getattr(debug_config, "debug_mode", False):
            return None

        try:
            sample_fraction = float(getattr(debug_config, "sample_fraction", 0.0))
        except (TypeError, ValueError):
            _log.debug(
                "Skipping CoSTEER timing extrapolation due to invalid sample_fraction=%r",
                getattr(debug_config, "sample_fraction", None),
            )
            return None

        if sample_fraction <= 0.0 or sample_fraction > 1.0:
            _log.debug(
                "Skipping CoSTEER timing extrapolation because sample_fraction must be within (0, 1], got %.6f",
                sample_fraction,
            )
            return None

        return sample_fraction

    def _record_debug_timing(
        self,
        experiment: ExperimentNode,
        scenario: ScenarioContext,
        round_idx: int,
        debug_time_sec: float,
    ) -> None:
        sample_fraction = self._get_debug_sample_fraction(scenario)
        if sample_fraction is None or not isinstance(experiment.hypothesis, dict):
            return

        estimated_full_time_sec = debug_time_sec / sample_fraction
        experiment.hypothesis["estimated_full_time_sec"] = estimated_full_time_sec
        _log.debug(
            "CoSTEER debug timing recorded for round %s: "
            "debug_time_sec=%.6f sample_fraction=%.6f estimated_full_time_sec=%.6f",
            round_idx,
            debug_time_sec,
            sample_fraction,
            estimated_full_time_sec,
        )

    def evolve(
        self,
        experiment: ExperimentNode,
        proposal: Proposal,
        scenario: ScenarioContext,
    ) -> CodeArtifact:
        artifact = self._coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)

        if self._max_rounds <= 1:
            return artifact

        for round_idx in range(1, self._max_rounds):
            round_started_at = time.monotonic()
            execution_result = self._runner.run(artifact, scenario)
            round_elapsed_sec = time.monotonic() - round_started_at
            self._record_debug_timing(experiment, scenario, round_idx, round_elapsed_sec)
            feedback = self._feedback_analyzer.summarize(
                experiment=experiment,
                result=execution_result,
                score=Score(
                    score_id=f"costeer-round-{round_idx}",
                    value=0.0,
                    metric_name="costeer",
                ),
            )
            outcome = execution_result.resolve_outcome()
            is_useful_round = outcome.process_succeeded and outcome.artifacts_verified and outcome.usefulness_eligible
            feedback.acceptable = feedback.acceptable and is_useful_round
            feedback.decision = feedback.decision and is_useful_round

            if feedback.acceptable:
                self._save_knowledge(experiment, feedback, round_idx, scenario)
                break

            if self._llm_adapter is not None:
                structured = self._analyze_feedback(
                    feedback_record=feedback,
                    code=getattr(artifact, "description", ""),
                    execution_output=getattr(execution_result, "logs_ref", ""),
                )
                if isinstance(experiment.hypothesis, dict):
                    experiment.hypothesis["_costeer_feedback"] = structured.reasoning
                    experiment.hypothesis["_costeer_feedback_execution"] = structured.execution
                    experiment.hypothesis["_costeer_feedback_code"] = structured.code
                    if structured.return_checking is not None:
                        experiment.hypothesis["_costeer_feedback_return"] = structured.return_checking
                    experiment.hypothesis["_costeer_round"] = round_idx + 1
            else:
                if isinstance(experiment.hypothesis, dict):
                    experiment.hypothesis["_costeer_feedback"] = feedback.reason
                    experiment.hypothesis["_costeer_round"] = round_idx + 1

            artifact = self._coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)

        return artifact

    def _save_knowledge(
        self,
        experiment: ExperimentNode,
        feedback: FeedbackRecord,
        round_idx: int,
        scenario: ScenarioContext,
    ) -> None:
        if self._llm_adapter is None or self._memory_service is None:
            return

        from llm.prompts import knowledge_extraction_prompt

        trace_summary = f"Hypothesis: {experiment.hypothesis}, Result: {feedback.reason}"
        prompt = knowledge_extraction_prompt(
            trace_summary=trace_summary,
            scenario=scenario.scenario_name,
        )
        knowledge_item = self._llm_adapter.complete(prompt)

        self._memory_service.write_memory(
            item=knowledge_item,
            metadata={
                "source": "costeer_knowledge_gen",
                "round": str(round_idx),
                "scenario": scenario.scenario_name,
            },
        )
