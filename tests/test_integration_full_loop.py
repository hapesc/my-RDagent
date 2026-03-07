from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.runtime import build_run_service, build_runtime
from core.loop.costeer import CoSTEEREvolver
from data_models import CodeArtifact, EventType, ExecutionResult, ExperimentNode, FeedbackRecord, Proposal, StopConditions
from llm.adapter import MockLLMProvider
from llm.providers.litellm_provider import LiteLLMProvider
from memory_service import MemoryService, MemoryServiceConfig
from plugins.contracts import ScenarioContext


class FullLoopIntegrationTests(unittest.TestCase):
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
                "RD_AGENT_LLM_PROVIDER": "mock",
            },
            clear=False,
        )
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def test_full_6_stage_single_step(self) -> None:
        runtime = build_runtime()
        run_service = build_run_service(runtime, "data_science")
        run = run_service.create_run(
            task_summary="integration smoke",
            stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
        )

        context = run_service.start_run(run.run_id, task_summary="integration smoke", loops_per_call=1)
        persisted = runtime.sqlite_store.get_run(run.run_id)
        run_session = context.run_session

        self.assertIsNotNone(context)
        self.assertIsNotNone(run_session)
        assert run_session is not None
        self.assertEqual(run_session.status.name, "COMPLETED")
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(persisted.status.name, "COMPLETED")

        events = runtime.sqlite_store.query_events(run_id=run.run_id)
        self.assertGreaterEqual(len(events), 6)
        event_types = {event.event_type for event in events}
        self.assertTrue(
            {
                EventType.HYPOTHESIS_GENERATED,
                EventType.EXPERIMENT_GENERATED,
                EventType.CODING_ROUND,
                EventType.EXECUTION_FINISHED,
                EventType.FEEDBACK_GENERATED,
                EventType.TRACE_RECORDED,
            }.issubset(event_types)
        )

    def test_costeer_multi_round_with_kb_write(self) -> None:
        experiment = ExperimentNode(
            node_id="node-costeer",
            run_id="run-costeer",
            branch_id="main",
            hypothesis={"idea": "reduce failure"},
        )
        proposal = Proposal(proposal_id="proposal-costeer", summary="improve retry strategy")
        scenario = ScenarioContext(
            run_id="run-costeer",
            scenario_name="data_science",
            input_payload={"task_summary": "costeer"},
            task_summary="costeer",
        )

        coder = Mock()
        coder.develop.side_effect = [
            CodeArtifact(artifact_id="artifact-1", description="first", location=self._tmpdir.name),
            CodeArtifact(artifact_id="artifact-2", description="second", location=self._tmpdir.name),
        ]
        runner = Mock()
        runner.run.return_value = ExecutionResult(
            run_id="run-costeer",
            exit_code=1,
            logs_ref="execution failed",
            artifacts_ref="[]",
        )
        feedback_analyzer = Mock()
        feedback_analyzer.summarize.side_effect = [
            FeedbackRecord(
                feedback_id="fb-1",
                decision=False,
                acceptable=False,
                reason="timeout observed",
            ),
            FeedbackRecord(
                feedback_id="fb-2",
                decision=True,
                acceptable=True,
                reason="recovered",
            ),
        ]

        evolver = CoSTEEREvolver(
            coder=coder,
            runner=runner,
            feedback_analyzer=feedback_analyzer,
            max_rounds=2,
        )
        final_artifact = evolver.evolve(experiment=experiment, proposal=proposal, scenario=scenario)

        self.assertEqual(coder.develop.call_count, 2)
        self.assertEqual(final_artifact.artifact_id, "artifact-2")

        memory_service = MemoryService(MemoryServiceConfig())
        first_feedback = feedback_analyzer.summarize.call_args_list[0][1]
        failure_reason = str(first_feedback["experiment"].hypothesis.get("_costeer_feedback", "timeout observed"))
        memory_service.write_memory(
            f"CoSTEER failure: {failure_reason}",
            {"step": "coding", "error_type": "timeout"},
        )
        context_pack = memory_service.query_context({"error_type": "timeout"})

        self.assertTrue(any("CoSTEER failure" in item for item in context_pack.items))

    def test_kb_cross_step_query(self) -> None:
        runtime = build_runtime()
        runtime.memory_service.write_memory("LLM timeout", {"step": "coding", "error_type": "timeout"})

        context_pack = runtime.memory_service.query_context({"error_type": "timeout"})

        self.assertTrue(any("LLM timeout" in item for item in context_pack.items))

    def test_llm_provider_switch(self) -> None:
        runtime_default = build_runtime()
        self.assertIsInstance(runtime_default.llm_adapter._provider, MockLLMProvider)

        with patch.dict(
            os.environ,
            {
                "RD_AGENT_LLM_PROVIDER": "litellm",
                "RD_AGENT_LLM_API_KEY": "test-key",
            },
            clear=False,
        ):
            runtime_litellm = build_runtime()

        self.assertIsInstance(runtime_litellm.llm_adapter._provider, LiteLLMProvider)


if __name__ == "__main__":
    unittest.main()
