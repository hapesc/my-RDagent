"""Task-12 tests for LLM adapter structured output and retries."""

from __future__ import annotations

import unittest

from data_models import (
    ContextPack,
    EventType,
    ExecutionResult,
    ExperimentNode,
    LoopState,
    Plan,
    RunSession,
    RunStatus,
    Score,
    StopConditions,
)
from llm import LLMAdapter, LLMAdapterConfig, MockLLMProvider, ProposalDraft
from plugins.examples import build_minimal_data_science_bundle


class SchemaWithoutFromDict:
    """Test class without from_dict method."""
    pass


class SchemaWithNonCallableFromDict:
    """Test class with non-callable from_dict attribute."""
    from_dict = "not-callable"


class LLMAdapterTests(unittest.TestCase):
    def test_mock_provider_returns_structured_proposal(self) -> None:
        adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=1))
        draft = adapter.generate_structured("proposal:improve baseline", ProposalDraft)
        self.assertEqual(draft.summary, "improve baseline")
        self.assertEqual(draft.constraints, ["llm-structured"])

    def test_retry_on_invalid_json_then_success(self) -> None:
        adapter = LLMAdapter(
            provider=MockLLMProvider(
                responses=[
                    "not-json",
                    '{"summary":"retry ok","constraints":[],"virtual_score":0.9}',
                ]
            ),
            config=LLMAdapterConfig(max_retries=2),
        )
        draft = adapter.generate_structured("proposal:any", ProposalDraft)
        self.assertEqual(draft.summary, "retry ok")
        self.assertAlmostEqual(draft.virtual_score, 0.9)

    def test_schema_without_from_dict_raises_type_error(self) -> None:
        adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=1))
        with self.assertRaises(ValueError) as ctx:
            adapter.generate_structured("proposal:any", SchemaWithoutFromDict)
        self.assertIn("structured output parse failed", str(ctx.exception))

    def test_schema_with_non_callable_from_dict_raises_type_error(self) -> None:
        adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=1))
        with self.assertRaises(ValueError) as ctx:
            adapter.generate_structured("proposal:any", SchemaWithNonCallableFromDict)
        self.assertIn("structured output parse failed", str(ctx.exception))

    def test_plugin_paths_use_llm_adapter(self) -> None:
        bundle = build_minimal_data_science_bundle()
        run_session = RunSession(
            run_id="run-task-12",
            scenario="data_science",
            status=RunStatus.RUNNING,
            stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
            entry_input={"task_id": "task-12"},
        )
        scenario = bundle.scenario_plugin.build_context(
            run_session=run_session,
            input_payload={"task_summary": "improve baseline"},
        )
        proposal = bundle.proposal_engine.propose(
            task_summary="improve baseline",
            context=ContextPack(items=[], highlights=[]),
            parent_ids=[],
            plan=Plan(plan_id="plan-12"),
            scenario=scenario,
        )
        experiment = bundle.experiment_generator.generate(
            proposal=proposal,
            run_session=run_session,
            loop_state=LoopState(loop_id="loop-12", iteration=0, status=RunStatus.RUNNING),
            parent_ids=[],
        )
        artifact = bundle.coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)
        feedback = bundle.feedback_analyzer.summarize(
            experiment=ExperimentNode(
                node_id="node-12",
                run_id="run-task-12",
                branch_id="main",
                loop_index=0,
            ),
            result=ExecutionResult(
                run_id="run-task-12",
                exit_code=0,
                logs_ref="logs",
                artifacts_ref="artifacts",
            ),
            score=Score(score_id="s", value=0.1, metric_name="acc"),
        )

        self.assertEqual(proposal.proposal_id, "proposal-llm")
        self.assertEqual(artifact.artifact_id, "artifact-llm")
        self.assertIn("succeeded", feedback.reason)


if __name__ == "__main__":
    unittest.main()
