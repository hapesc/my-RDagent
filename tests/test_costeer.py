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

    def test_knowledge_saved_on_success(self) -> None:
        """Test that knowledge is extracted and saved when feedback is acceptable."""
        from core.loop.costeer import CoSTEEREvolver

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        llm_adapter = MagicMock()
        memory_service = MagicMock()

        artifact_v1 = CodeArtifact(artifact_id="v1", description="first", location="/tmp/v1")
        coder.develop.return_value = artifact_v1

        execution_result = ExecutionResult(run_id="run-1", exit_code=0, logs_ref="", artifacts_ref="")
        runner.run.return_value = execution_result

        feedback_good = FeedbackRecord(
            feedback_id="fb1",
            decision=True,
            acceptable=True,
            reason="looks good",
        )
        feedback_analyzer.summarize.return_value = feedback_good
        llm_adapter.complete.return_value = "learned: feature X works well in test scenario"

        evolver = CoSTEEREvolver(
            coder=coder,
            runner=runner,
            feedback_analyzer=feedback_analyzer,
            max_rounds=3,
            llm_adapter=llm_adapter,
            memory_service=memory_service,
        )
        experiment, proposal, scenario = self._base_inputs()

        result = evolver.evolve(experiment, proposal, scenario)

        self.assertEqual(memory_service.write_memory.call_count, 1)
        call_args = memory_service.write_memory.call_args
        self.assertIsNotNone(call_args)
        
        item = call_args.kwargs.get("item")
        self.assertIsNotNone(item)
        self.assertIsInstance(item, str)
        self.assertGreater(len(item), 0)
        
        metadata = call_args.kwargs.get("metadata")
        self.assertIsNotNone(metadata)
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata.get("source"), "costeer_knowledge_gen")

    def test_knowledge_not_saved_on_failure(self) -> None:
        """Test that knowledge is NOT saved when all feedback is unacceptable."""
        from core.loop.costeer import CoSTEEREvolver

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        llm_adapter = MagicMock()
        memory_service = MagicMock()

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
        feedback_analyzer.summarize.return_value = feedback_bad

        evolver = CoSTEEREvolver(
            coder=coder,
            runner=runner,
            feedback_analyzer=feedback_analyzer,
            max_rounds=2,
            llm_adapter=llm_adapter,
            memory_service=memory_service,
        )
        experiment, proposal, scenario = self._base_inputs()

        result = evolver.evolve(experiment, proposal, scenario)

        memory_service.write_memory.assert_not_called()

    def test_no_memory_service_no_error(self) -> None:
        """Test that evolver works normally without memory_service."""
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
            memory_service=None,
        )
        experiment, proposal, scenario = self._base_inputs()

        result = evolver.evolve(experiment, proposal, scenario)

        self.assertEqual(result, artifact_v1)
        self.assertEqual(coder.develop.call_count, 1)
        self.assertEqual(runner.run.call_count, 1)

    def test_structured_feedback_generated_on_failure_round(self) -> None:
        from core.loop.costeer import CoSTEEREvolver
        from llm.schemas import StructuredFeedback

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        llm_adapter = MagicMock()

        artifact_v1 = CodeArtifact(artifact_id="v1", description="first", location="/tmp/v1")
        artifact_v2 = CodeArtifact(artifact_id="v2", description="second", location="/tmp/v2")
        coder.develop.side_effect = [artifact_v1, artifact_v2]

        execution_result = ExecutionResult(run_id="run-1", exit_code=0, logs_ref="some logs", artifacts_ref="")
        runner.run.return_value = execution_result

        feedback_bad = FeedbackRecord(feedback_id="fb1", decision=False, acceptable=False, reason="needs work")
        feedback_good = FeedbackRecord(feedback_id="fb2", decision=True, acceptable=True, reason="ok")
        feedback_analyzer.summarize.side_effect = [feedback_bad, feedback_good]

        mock_structured = StructuredFeedback(
            execution="ran ok",
            return_checking="values off",
            code="needs refactor",
            final_decision=False,
            reasoning="overall poor",
        )
        llm_adapter.generate_structured.return_value = mock_structured

        evolver = CoSTEEREvolver(
            coder=coder, runner=runner, feedback_analyzer=feedback_analyzer,
            max_rounds=3, llm_adapter=llm_adapter,
        )
        experiment, proposal, scenario = self._base_inputs()
        evolver.evolve(experiment, proposal, scenario)

        llm_adapter.generate_structured.assert_called_once()
        self.assertEqual(experiment.hypothesis.get("_costeer_feedback"), "overall poor")
        self.assertEqual(experiment.hypothesis.get("_costeer_feedback_execution"), "ran ok")
        self.assertEqual(experiment.hypothesis.get("_costeer_feedback_code"), "needs refactor")
        self.assertEqual(experiment.hypothesis.get("_costeer_feedback_return"), "values off")

    def test_structured_feedback_three_dimensions_populated(self) -> None:
        from core.loop.costeer import CoSTEEREvolver
        from llm.schemas import StructuredFeedback

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        llm_adapter = MagicMock()

        artifact = CodeArtifact(artifact_id="v1", description="code", location="/tmp/v1")
        coder.develop.return_value = artifact
        runner.run.return_value = ExecutionResult(run_id="run-1", exit_code=1, logs_ref="error", artifacts_ref="")

        feedback_bad = FeedbackRecord(feedback_id="fb1", decision=False, acceptable=False, reason="fail")
        feedback_analyzer.summarize.return_value = feedback_bad

        mock_sf = StructuredFeedback(
            execution="crashed",
            return_checking=None,
            code="syntax error",
            final_decision=False,
            reasoning="bad code",
        )
        llm_adapter.generate_structured.return_value = mock_sf

        evolver = CoSTEEREvolver(
            coder=coder, runner=runner, feedback_analyzer=feedback_analyzer,
            max_rounds=2, llm_adapter=llm_adapter,
        )
        experiment, proposal, scenario = self._base_inputs()
        evolver.evolve(experiment, proposal, scenario)

        self.assertIn("_costeer_feedback_execution", experiment.hypothesis)
        self.assertIn("_costeer_feedback_code", experiment.hypothesis)
        self.assertNotIn("_costeer_feedback_return", experiment.hypothesis)

    def test_no_llm_adapter_falls_back_to_plain_feedback(self) -> None:
        from core.loop.costeer import CoSTEEREvolver

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()

        artifact_v1 = CodeArtifact(artifact_id="v1", description="first", location="/tmp/v1")
        artifact_v2 = CodeArtifact(artifact_id="v2", description="second", location="/tmp/v2")
        coder.develop.side_effect = [artifact_v1, artifact_v2]

        runner.run.return_value = ExecutionResult(run_id="run-1", exit_code=0, logs_ref="", artifacts_ref="")

        feedback_bad = FeedbackRecord(feedback_id="fb1", decision=False, acceptable=False, reason="plain text feedback")
        feedback_good = FeedbackRecord(feedback_id="fb2", decision=True, acceptable=True, reason="ok")
        feedback_analyzer.summarize.side_effect = [feedback_bad, feedback_good]

        evolver = CoSTEEREvolver(
            coder=coder, runner=runner, feedback_analyzer=feedback_analyzer,
            max_rounds=3, llm_adapter=None,
        )
        experiment, proposal, scenario = self._base_inputs()
        evolver.evolve(experiment, proposal, scenario)

        self.assertEqual(experiment.hypothesis.get("_costeer_feedback"), "plain text feedback")
        self.assertNotIn("_costeer_feedback_execution", experiment.hypothesis)
        self.assertNotIn("_costeer_feedback_code", experiment.hypothesis)

    def test_analyze_feedback_calls_structured_prompt(self) -> None:
        from core.loop.costeer import CoSTEEREvolver
        from llm.schemas import StructuredFeedback

        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()
        llm_adapter = MagicMock()

        mock_sf = StructuredFeedback(execution="ok", code="ok", reasoning="ok")
        llm_adapter.generate_structured.return_value = mock_sf

        evolver = CoSTEEREvolver(
            coder=coder, runner=runner, feedback_analyzer=feedback_analyzer,
            llm_adapter=llm_adapter,
        )

        fb = FeedbackRecord(feedback_id="fb1", decision=False, acceptable=False, reason="test reason")
        result = evolver._analyze_feedback(fb, code="print(1)", execution_output="error")

        self.assertIsInstance(result, StructuredFeedback)
        llm_adapter.generate_structured.assert_called_once()
        call_args = llm_adapter.generate_structured.call_args
        prompt_arg = call_args[0][0]
        self.assertIn("test reason", prompt_arg)
        self.assertIn("print(1)", prompt_arg)
        self.assertEqual(call_args[0][1], StructuredFeedback)


if __name__ == "__main__":
    unittest.main()
