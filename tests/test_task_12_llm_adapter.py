"""Task-12 tests for LLM adapter structured output and retries."""

from __future__ import annotations

import unittest

from data_models import (
    ContextPack,
    ExecutionResult,
    ExperimentNode,
    LoopState,
    Plan,
    RunSession,
    RunStatus,
    Score,
    StopConditions,
)
from llm import CodeDraft, LLMAdapter, LLMAdapterConfig, MockLLMProvider, ProposalDraft
from llm.adapter import StructuredOutputParseError
from plugins.examples import build_minimal_data_science_bundle
from service_contracts import ModelSelectorConfig


class SchemaWithoutFromDict:
    """Test class without from_dict method."""

    pass


class SchemaWithNonCallableFromDict:
    """Test class with non-callable from_dict attribute."""

    from_dict = "not-callable"


class CountingResponsesProvider:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str:
        self.calls += 1
        return self._responses.pop(0)


class DisconnectThenRecoverProvider:
    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str:
        _ = prompt
        _ = model_config
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, str):
            raise TypeError(f"unexpected response type: {type(response).__name__}")
        return response


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

    def test_missing_required_fields_retries_then_fails_with_diagnostics(self) -> None:
        provider = MockLLMProvider(
            responses=[
                '{"summary":"only-summary"}',
                '{"summary":"still-missing"}',
            ]
        )
        adapter = LLMAdapter(provider=provider, config=LLMAdapterConfig(max_retries=1))
        with self.assertRaises(StructuredOutputParseError) as ctx:
            adapter.generate_structured("proposal:any", ProposalDraft)

        self.assertIn("required_fields", str(ctx.exception))
        self.assertEqual(len(ctx.exception.diagnostics), 2)
        self.assertEqual(ctx.exception.retry_count, 1)
        self.assertEqual(ctx.exception.failure_counts, {"required_fields": 2})
        self.assertTrue(all(d.retryable for d in ctx.exception.diagnostics))

    def test_wrong_type_virtual_score_is_rejected(self) -> None:
        adapter = LLMAdapter(
            provider=MockLLMProvider(responses=['{"summary":"ok","constraints":[],"virtual_score":"0.9"}']),
            config=LLMAdapterConfig(max_retries=0),
        )

        with self.assertRaises(StructuredOutputParseError) as ctx:
            adapter.generate_structured("proposal:any", ProposalDraft)

        self.assertIn("field type validation failed", str(ctx.exception))
        self.assertEqual(ctx.exception.failure_counts, {"field_types": 1})

    def test_wrong_type_constraints_is_rejected(self) -> None:
        adapter = LLMAdapter(
            provider=MockLLMProvider(responses=['{"summary":"ok","constraints":"x","virtual_score":0.9}']),
            config=LLMAdapterConfig(max_retries=0),
        )

        with self.assertRaises(StructuredOutputParseError) as ctx:
            adapter.generate_structured("proposal:any", ProposalDraft)

        self.assertIn("field type validation failed", str(ctx.exception))
        self.assertEqual(ctx.exception.failure_counts, {"field_types": 1})

    def test_non_object_payload_emits_deterministic_failure_markers(self) -> None:
        adapter = LLMAdapter(
            provider=MockLLMProvider(responses=['["not","an","object"]']),
            config=LLMAdapterConfig(max_retries=0),
        )

        with self.assertRaises(StructuredOutputParseError) as ctx:
            adapter.generate_structured("proposal:any", ProposalDraft)

        self.assertEqual(ctx.exception.retry_count, 0)
        self.assertEqual(ctx.exception.failure_counts, {"payload_type": 1})
        self.assertEqual(ctx.exception.failure_stages, ("payload_type",))

    def test_provider_disconnect_retries_then_succeeds(self) -> None:
        provider = DisconnectThenRecoverProvider(
            responses=[
                ConnectionError("provider socket closed"),
                '{"summary":"recovered","constraints":["ok"],"virtual_score":0.7}',
            ]
        )
        adapter = LLMAdapter(provider=provider, config=LLMAdapterConfig(max_retries=1))

        draft = adapter.generate_structured("proposal:any", ProposalDraft)

        self.assertEqual(provider.calls, 2)
        self.assertEqual(draft.summary, "recovered")
        self.assertEqual(draft.constraints, ["ok"])

    def test_schema_error_is_permanent_and_stops_retries(self) -> None:
        provider = CountingResponsesProvider(
            responses=[
                '{"summary":"x","constraints":[],"virtual_score":0.2}',
                '{"summary":"y","constraints":[],"virtual_score":0.3}',
            ]
        )
        adapter = LLMAdapter(provider=provider, config=LLMAdapterConfig(max_retries=3))

        with self.assertRaises(StructuredOutputParseError) as ctx:
            adapter.generate_structured("proposal:any", SchemaWithoutFromDict)

        self.assertEqual(provider.calls, 1)
        self.assertIn("stage=schema", str(ctx.exception))

    def test_generate_code_parses_metadata_and_strips_code_fence(self) -> None:
        provider = MockLLMProvider(
            responses=[
                """
                metadata:
                {"artifact_id":"artifact-llm","description":"desc","location":"/tmp/ws"}

                ```python
                print('ok')
                ```
                """
            ]
        )
        adapter = LLMAdapter(provider=provider, config=LLMAdapterConfig(max_retries=0))

        metadata, code = adapter.generate_code("coding:any", CodeDraft)

        self.assertEqual(metadata.artifact_id, "artifact-llm")
        self.assertEqual(code, "print('ok')")

    def test_repair_json_allows_trailing_comma_recovery(self) -> None:
        adapter = LLMAdapter(
            provider=MockLLMProvider(responses=['{"summary":"ok","constraints":[],"virtual_score":0.4,}']),
            config=LLMAdapterConfig(max_retries=0),
        )
        broken = '{"summary":"ok","constraints":[],"virtual_score":0.4,}'
        repaired = adapter._repair_json(broken)
        self.assertNotIn(",}", repaired)
        parsed = adapter.generate_structured("proposal:any", ProposalDraft)
        self.assertIsInstance(parsed, ProposalDraft)

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
        self.assertTrue(
            artifact.artifact_id.startswith("artifact-"),
            f"Expected artifact_id to start with 'artifact-', got '{artifact.artifact_id}'",
        )
        self.assertIn("succeeded", feedback.reason)


if __name__ == "__main__":
    unittest.main()
