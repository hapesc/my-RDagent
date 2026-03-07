from __future__ import annotations

from data_models import CodeArtifact, ExperimentNode, Proposal, Score
from plugins.contracts import Coder, FeedbackAnalyzer, Runner, ScenarioContext


class CoSTEEREvolver:
    def __init__(
        self,
        coder: Coder,
        runner: Runner,
        feedback_analyzer: FeedbackAnalyzer,
        max_rounds: int = 3,
    ) -> None:
        self._coder = coder
        self._runner = runner
        self._feedback_analyzer = feedback_analyzer
        self._max_rounds = max_rounds

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
            execution_result = self._runner.run(artifact, scenario)
            feedback = self._feedback_analyzer.summarize(
                experiment=experiment,
                result=execution_result,
                score=Score(
                    score_id=f"costeer-round-{round_idx}",
                    value=0.0,
                    metric_name="costeer",
                ),
            )
            if feedback.acceptable:
                break
            if isinstance(experiment.hypothesis, dict):
                experiment.hypothesis["_costeer_feedback"] = feedback.reason
                experiment.hypothesis["_costeer_round"] = round_idx + 1
            artifact = self._coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)

        return artifact
