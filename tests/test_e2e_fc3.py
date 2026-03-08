from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.runtime import build_run_service, build_runtime
from core.loop.costeer import CoSTEEREvolver
from core.reasoning.pipeline import ReasoningPipeline
from data_models import (
    CodeArtifact,
    EventType,
    ExecutionResult,
    ExperimentNode,
    FeedbackRecord,
    Proposal,
    StopConditions,
)
from llm.adapter import LLMAdapter, MockLLMProvider
from llm.schemas import ReasoningTrace, StructuredFeedback
from plugins.contracts import ScenarioContext


class TestFC3E2E(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._env_patch = patch.dict(
            os.environ,
            {
                "AGENTRD_ARTIFACT_ROOT": self._tmpdir.name,
                "AGENTRD_WORKSPACE_ROOT": self._tmpdir.name,
                "AGENTRD_TRACE_STORAGE_PATH": os.path.join(self._tmpdir.name, "trace", "events.jsonl"),
                "AGENTRD_SQLITE_PATH": os.path.join(self._tmpdir.name, "meta.db"),
                "AGENTRD_ALLOW_LOCAL_EXECUTION": "true",
                "RD_AGENT_COSTEER_MAX_ROUNDS": "2",
                "RD_AGENT_LLM_PROVIDER": "mock",
            },
            clear=False,
        )
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def _base_costeer_inputs(self) -> tuple[ExperimentNode, Proposal, ScenarioContext]:
        experiment = ExperimentNode(
            node_id="n-fc3",
            run_id="run-fc3",
            branch_id="main",
            hypothesis={},
        )
        proposal = Proposal(proposal_id="p-fc3", summary="fc3 proposal")
        scenario = ScenarioContext(
            run_id="run-fc3",
            scenario_name="data_science",
            input_payload={},
            task_summary="fc3 test",
        )
        return experiment, proposal, scenario

    def test_costeer_structured_feedback_e2e(self) -> None:
        adapter = LLMAdapter(MockLLMProvider())
        coder = MagicMock()
        runner = MagicMock()
        feedback_analyzer = MagicMock()

        artifact_v1 = CodeArtifact(artifact_id="a1", description="print('hello')", location="/tmp/a1")
        artifact_v2 = CodeArtifact(artifact_id="a2", description="print('hello')", location="/tmp/a2")
        coder.develop.side_effect = [artifact_v1, artifact_v2]
        runner.run.return_value = ExecutionResult(
            run_id="run-fc3",
            exit_code=1,
            logs_ref="runtime output",
            artifacts_ref="",
        )
        feedback_bad = FeedbackRecord(
            feedback_id="fb-bad",
            decision=False,
            acceptable=False,
            reason="execution failed",
        )
        feedback_analyzer.summarize.return_value = feedback_bad

        evolver = CoSTEEREvolver(
            coder=coder,
            runner=runner,
            feedback_analyzer=feedback_analyzer,
            max_rounds=2,
            llm_adapter=adapter,
            memory_service=MagicMock(),
        )
        experiment, proposal, scenario = self._base_costeer_inputs()

        result = evolver.evolve(experiment=experiment, proposal=proposal, scenario=scenario)

        self.assertEqual(result.artifact_id, "a2")
        self.assertIn("_costeer_feedback_execution", experiment.hypothesis)
        self.assertIn("_costeer_feedback_return", experiment.hypothesis)
        self.assertIn("_costeer_feedback_code", experiment.hypothesis)

        structured = evolver._analyze_feedback(
            feedback_record=feedback_bad,
            code="print('hello')",
            execution_output="runtime output",
        )
        self.assertIsInstance(structured, StructuredFeedback)
        self.assertTrue(bool(structured.execution.strip()))
        self.assertTrue(bool((structured.return_checking or "").strip()))
        self.assertTrue(bool(structured.code.strip()))

    def test_costeer_knowledge_self_gen_e2e(self) -> None:
        adapter = LLMAdapter(MockLLMProvider())

        def complete_stub(prompt: str) -> str:
            return "mock knowledge"

        setattr(adapter, "complete", complete_stub)
        success_memory = MagicMock()
        fail_memory = MagicMock()

        success_coder = MagicMock()
        success_runner = MagicMock()
        success_feedback = MagicMock()
        success_coder.develop.return_value = CodeArtifact(
            artifact_id="success",
            description="ok",
            location="/tmp/success",
        )
        success_runner.run.return_value = ExecutionResult(
            run_id="run-fc3",
            exit_code=0,
            logs_ref="all good",
            artifacts_ref="",
        )
        success_feedback.summarize.return_value = FeedbackRecord(
            feedback_id="fb-ok",
            decision=True,
            acceptable=True,
            reason="acceptable",
        )
        success_evolver = CoSTEEREvolver(
            coder=success_coder,
            runner=success_runner,
            feedback_analyzer=success_feedback,
            max_rounds=2,
            llm_adapter=adapter,
            memory_service=success_memory,
        )
        success_experiment, success_proposal, success_scenario = self._base_costeer_inputs()
        success_evolver.evolve(success_experiment, success_proposal, success_scenario)
        success_memory.write_memory.assert_called_once()

        fail_coder = MagicMock()
        fail_runner = MagicMock()
        fail_feedback = MagicMock()
        fail_coder.develop.side_effect = [
            CodeArtifact(artifact_id="f1", description="bad", location="/tmp/f1"),
            CodeArtifact(artifact_id="f2", description="still bad", location="/tmp/f2"),
        ]
        fail_runner.run.return_value = ExecutionResult(
            run_id="run-fc3",
            exit_code=1,
            logs_ref="failed",
            artifacts_ref="",
        )
        fail_feedback.summarize.return_value = FeedbackRecord(
            feedback_id="fb-fail",
            decision=False,
            acceptable=False,
            reason="unacceptable",
        )
        fail_evolver = CoSTEEREvolver(
            coder=fail_coder,
            runner=fail_runner,
            feedback_analyzer=fail_feedback,
            max_rounds=2,
            llm_adapter=adapter,
            memory_service=fail_memory,
        )
        fail_experiment, fail_proposal, fail_scenario = self._base_costeer_inputs()
        fail_evolver.evolve(fail_experiment, fail_proposal, fail_scenario)
        fail_memory.write_memory.assert_not_called()

    def test_reasoning_trace_persisted_e2e(self) -> None:
        adapter = LLMAdapter(MockLLMProvider())
        trace_store = MagicMock()
        pipeline = ReasoningPipeline(llm_adapter=adapter, trace_store=trace_store)

        result = pipeline.reason(
            task_summary="test",
            scenario_name="data_science",
            iteration=0,
            previous_results=[],
            current_scores=[],
        )

        self.assertTrue(bool(result.summary.strip()))
        trace_store.store.assert_called_once()
        stored_trace = trace_store.store.call_args[0][0]
        self.assertIsInstance(stored_trace, ReasoningTrace)
        self.assertEqual(set(stored_trace.stages.keys()), {"analysis", "problem", "hypothesis", "design"})

    def test_fc3_full_loop_with_trace_and_feedback(self) -> None:
        runtime = build_runtime()
        run_service = build_run_service(runtime, "data_science")
        run = run_service.create_run(
            task_summary="classify iris dataset",
            stop_conditions=StopConditions(max_loops=2, max_duration_sec=120),
        )

        context = run_service.start_run(
            run.run_id,
            task_summary="classify iris dataset",
            loops_per_call=2,
        )

        self.assertIsNotNone(context)
        assert context.run_session is not None
        self.assertEqual(context.run_session.status.name, "COMPLETED")

        events = runtime.sqlite_store.query_events(run_id=run.run_id)
        event_types = {event.event_type for event in events}
        proposal_events = [event for event in events if event.event_type == EventType.HYPOTHESIS_GENERATED]
        self.assertIn(EventType.FEEDBACK_GENERATED, event_types)
        self.assertIn(EventType.TRACE_RECORDED, event_types)
        self.assertTrue(proposal_events)
        self.assertEqual(proposal_events[0].payload.get("proposal_id"), "proposal-ds-fc3")

        trace_entries = runtime.memory_service.query_context({"kind": "reasoning_trace"})
        self.assertTrue(trace_entries.items)


if __name__ == "__main__":
    unittest.main()
