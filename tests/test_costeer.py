"""Tests for CoSTEER multi-round evolution loop."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from data_models import (
    CodeArtifact,
    ExecutionResult,
    ExperimentNode,
    FeedbackRecord,
    Proposal,
    Score,
)
from plugins.contracts import ScenarioContext


class CoSTEEREvolverTests(unittest.TestCase):
    def _base_inputs(self):
        experiment = ExperimentNode(
            node_id="n1",
            run_id="run-1",
            branch_id="main",
            hypothesis={},
        )
        proposal = Proposal(proposal_id="p1", summary="test")
        scenario = ScenarioContext(run_id="run-1", scenario_name="test", input_payload={})
        return experiment, proposal, scenario

    def test_single_round_mode(self) -> None:
        from core.loop.costeer import CoSTEEREvolver

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        artifact = CodeArtifact(artifact_id="v1", description="only", location="/tmp/v1")
        coder.develop.return_value = artifact

        evolver = CoSTEEREvolver(
            coder=coder,
            runner=runner,
            feedback_analyzer=feedback_analyzer,
            max_rounds=1,
        )
        experiment, proposal, scenario = self._base_inputs()

        result = evolver.evolve(experiment, proposal, scenario)

        self.assertEqual(result, artifact)
        self.assertEqual(coder.develop.call_count, 1)
        runner.run.assert_not_called()
        feedback_analyzer.summarize.assert_not_called()

    def test_multi_round_acceptable_after_2(self) -> None:
        from core.loop.costeer import CoSTEEREvolver

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        artifact_v1 = CodeArtifact(artifact_id="v1", description="first", location="/tmp/v1")
        artifact_v2 = CodeArtifact(artifact_id="v2", description="second", location="/tmp/v2")
        coder.develop.side_effect = [artifact_v1, artifact_v2]

        execution_result = ExecutionResult(run_id="run-1", exit_code=0, logs_ref="", artifacts_ref="")
        runner.run.return_value = execution_result

        feedback_bad = FeedbackRecord(
            feedback_id="fb1",
            decision=False,
            acceptable=False,
            reason="need improvement",
        )
        feedback_good = FeedbackRecord(
            feedback_id="fb2",
            decision=True,
            acceptable=True,
            reason="looks good",
        )
        feedback_analyzer.summarize.side_effect = [feedback_bad, feedback_good]

        evolver = CoSTEEREvolver(
            coder=coder,
            runner=runner,
            feedback_analyzer=feedback_analyzer,
            max_rounds=3,
        )
        experiment, proposal, scenario = self._base_inputs()

        result = evolver.evolve(experiment, proposal, scenario)

        self.assertEqual(result, artifact_v2)
        self.assertEqual(coder.develop.call_count, 2)
        self.assertEqual(runner.run.call_count, 2)
        self.assertEqual(feedback_analyzer.summarize.call_count, 2)
        self.assertEqual(experiment.hypothesis.get("_costeer_feedback"), "need improvement")
        self.assertEqual(experiment.hypothesis.get("_costeer_round"), 2)

    def test_max_rounds_reached(self) -> None:
        from core.loop.costeer import CoSTEEREvolver

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        artifact_v1 = CodeArtifact(artifact_id="v1", description="first", location="/tmp/v1")
        artifact_v2 = CodeArtifact(artifact_id="v2", description="second", location="/tmp/v2")
        coder.develop.side_effect = [artifact_v1, artifact_v2]

        execution_result = ExecutionResult(run_id="run-1", exit_code=0, logs_ref="", artifacts_ref="")
        runner.run.return_value = execution_result
        feedback_bad = FeedbackRecord(
            feedback_id="fb1",
            decision=False,
            acceptable=False,
            reason="still bad",
        )
        feedback_analyzer.summarize.return_value = feedback_bad

        evolver = CoSTEEREvolver(
            coder=coder,
            runner=runner,
            feedback_analyzer=feedback_analyzer,
            max_rounds=2,
        )
        experiment, proposal, scenario = self._base_inputs()

        result = evolver.evolve(experiment, proposal, scenario)

        self.assertEqual(result, artifact_v2)
        self.assertEqual(coder.develop.call_count, 2)
        self.assertEqual(runner.run.call_count, 1)
        self.assertEqual(feedback_analyzer.summarize.call_count, 1)

    def test_first_round_acceptable(self) -> None:
        from core.loop.costeer import CoSTEEREvolver

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        artifact_v1 = CodeArtifact(artifact_id="v1", description="first", location="/tmp/v1")
        coder.develop.return_value = artifact_v1

        execution_result = ExecutionResult(run_id="run-1", exit_code=0, logs_ref="", artifacts_ref="")
        runner.run.return_value = execution_result
        feedback_good = FeedbackRecord(
            feedback_id="fb1",
            decision=True,
            acceptable=True,
            reason="good enough",
        )
        feedback_analyzer.summarize.return_value = feedback_good

        evolver = CoSTEEREvolver(
            coder=coder,
            runner=runner,
            feedback_analyzer=feedback_analyzer,
            max_rounds=3,
        )
        experiment, proposal, scenario = self._base_inputs()

        result = evolver.evolve(experiment, proposal, scenario)

        self.assertEqual(result, artifact_v1)
        self.assertEqual(coder.develop.call_count, 1)
        self.assertEqual(runner.run.call_count, 1)
        self.assertEqual(feedback_analyzer.summarize.call_count, 1)

    def test_feedback_score_is_stubbed(self) -> None:
        from core.loop.costeer import CoSTEEREvolver

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        artifact_v1 = CodeArtifact(artifact_id="v1", description="first", location="/tmp/v1")
        artifact_v2 = CodeArtifact(artifact_id="v2", description="second", location="/tmp/v2")
        coder.develop.side_effect = [artifact_v1, artifact_v2]

        execution_result = ExecutionResult(run_id="run-1", exit_code=0, logs_ref="", artifacts_ref="")
        runner.run.return_value = execution_result
        feedback_analyzer.summarize.return_value = FeedbackRecord(
            feedback_id="fb1",
            decision=False,
            acceptable=False,
            reason="retry",
        )

        evolver = CoSTEEREvolver(
            coder=coder,
            runner=runner,
            feedback_analyzer=feedback_analyzer,
            max_rounds=2,
        )
        experiment, proposal, scenario = self._base_inputs()

        evolver.evolve(experiment, proposal, scenario)

        summarize_kwargs = feedback_analyzer.summarize.call_args.kwargs
        score = summarize_kwargs["score"]
        self.assertIsInstance(score, Score)
        self.assertEqual(score.score_id, "costeer-round-1")
        self.assertEqual(score.value, 0.0)
        self.assertEqual(score.metric_name, "costeer")


if __name__ == "__main__":
    unittest.main()
