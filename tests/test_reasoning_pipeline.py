# pyright: reportMissingImports=false
from __future__ import annotations

import pytest

from core.reasoning.pipeline import ReasoningPipeline
from llm.adapter import LLMAdapter, LLMAdapterConfig, MockLLMProvider, StructuredOutputParseError
from llm.schemas import (
    AnalysisResult,
    ExperimentDesign,
    HypothesisFormulation,
    ProblemIdentification,
    ReasoningTrace,
)
from service_contracts import ModelSelectorConfig


class CountingProvider:
    def __init__(self, inner: MockLLMProvider) -> None:
        self._inner = inner
        self.calls = 0
        self.model_configs = []

    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str:
        self.calls += 1
        self.model_configs.append(model_config)
        return self._inner.complete(prompt, model_config=model_config)


class AlwaysInvalidJSONProvider:
    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str:
        return "not-json"


class MissingRequiredFieldsProvider:
    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str:
        return '{"strengths":["ok"]}'


class SequencedProvider:
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


class RecordingTraceStore:
    def __init__(self) -> None:
        self.calls = 0
        self.records = []

    def store(self, trace: ReasoningTrace) -> None:
        self.calls += 1
        self.records.append(trace)


def _make_pipeline() -> ReasoningPipeline:
    return ReasoningPipeline(LLMAdapter(MockLLMProvider()))


def test_pipeline_returns_experiment_design() -> None:
    provider = MockLLMProvider(
        responses=[
            ('{"strengths":["s1"],"weaknesses":["w1"],"current_performance":"stable","key_observations":"obs"}'),
            ('{"problem":"p1","severity":"high","evidence":"e1","affected_component":"optimizer"}'),
            ('{"hypothesis":"h1","mechanism":"m1","expected_improvement":"+3%","testable_prediction":"tp1"}'),
            (
                '{"summary":"exp design","constraints":["c1"],'
                '"virtual_score":0.8,"implementation_steps":["step1","step2"]}'
            ),
        ]
    )
    pipeline = ReasoningPipeline(LLMAdapter(provider))

    result = pipeline.reason(
        task_summary="Improve baseline accuracy",
        scenario_name="data_science",
        iteration=1,
        previous_results=["Run 0 reached 0.71 accuracy"],
        current_scores=[0.71],
    )

    assert isinstance(result, ExperimentDesign)
    assert result.summary
    assert result.implementation_steps


def test_pipeline_four_stages_called() -> None:
    counting_provider = CountingProvider(MockLLMProvider())
    pipeline = ReasoningPipeline(LLMAdapter(counting_provider))

    pipeline.reason(
        task_summary="Tune optimizer settings",
        scenario_name="data_science",
        iteration=2,
        previous_results=["SGD converges slowly"],
        current_scores=[0.62],
    )

    assert counting_provider.calls >= 4


def test_pipeline_with_previous_results() -> None:
    pipeline = _make_pipeline()

    result = pipeline.reason(
        task_summary="Improve F1 score",
        scenario_name="data_science",
        iteration=3,
        previous_results=[
            "Run 0: baseline features",
            "Run 1: feature scaling",
            "Run 2: tuned regularization",
        ],
        current_scores=[0.58, 0.63, 0.66],
    )

    assert isinstance(result, ExperimentDesign)
    assert result.summary != ""


def test_pipeline_first_iteration() -> None:
    pipeline = _make_pipeline()

    result = pipeline.reason(
        task_summary="Establish first executable baseline",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )

    assert isinstance(result, ExperimentDesign)
    assert result.summary


def test_pipeline_passes_model_config() -> None:
    counting_provider = CountingProvider(MockLLMProvider())
    pipeline = ReasoningPipeline(LLMAdapter(counting_provider))
    model_config = ModelSelectorConfig(
        provider="mock-provider",
        model="mock-model",
        temperature=0.2,
        max_tokens=400,
    )

    pipeline.reason(
        task_summary="Optimize memory usage",
        scenario_name="systems",
        iteration=1,
        previous_results=["Memory spikes on large batch"],
        current_scores=[0.5],
        model_config=model_config,
    )

    assert counting_provider.calls >= 4
    assert counting_provider.model_configs[:4] == [model_config, model_config, model_config, model_config]


def test_build_reasoning_trace() -> None:
    pipeline = _make_pipeline()

    trace = pipeline._build_reasoning_trace(
        analysis=AnalysisResult(),
        problem=ProblemIdentification(),
        hypothesis=HypothesisFormulation(),
        design=ExperimentDesign(),
    )

    assert isinstance(trace, dict)
    assert set(trace.keys()) == {"analysis", "problem", "hypothesis", "design"}


def test_build_reasoning_trace_content() -> None:
    pipeline = _make_pipeline()
    analysis = AnalysisResult(
        strengths=["stable training"],
        weaknesses=["overfitting"],
        current_performance="0.74 accuracy",
        key_observations="validation loss diverges after epoch 8",
    )
    problem = ProblemIdentification(
        problem="regularization too weak",
        severity="high",
        evidence="train/val gap expands",
        affected_component="training_loop",
    )
    hypothesis = HypothesisFormulation(
        hypothesis="If dropout is increased, then generalization will improve",
        mechanism="stronger regularization reduces co-adaptation",
        expected_improvement="+2-3% accuracy",
        testable_prediction="smaller train/val gap",
    )
    design = ExperimentDesign(
        summary="Increase dropout from 0.2 to 0.4 and compare validation accuracy",
        constraints=["possible underfitting"],
        virtual_score=0.68,
        implementation_steps=["Update model config", "Run 3 seeds", "Compare metrics"],
    )

    trace = pipeline._build_reasoning_trace(analysis, problem, hypothesis, design)

    assert trace["analysis"]["strengths"] == ["stable training"]
    assert trace["analysis"]["weaknesses"] == ["overfitting"]
    assert trace["analysis"]["current_performance"] == "0.74 accuracy"
    assert trace["analysis"]["key_observations"] == "validation loss diverges after epoch 8"
    assert trace["problem"]["problem"] == "regularization too weak"
    assert trace["problem"]["severity"] == "high"
    assert trace["problem"]["evidence"] == "train/val gap expands"
    assert trace["problem"]["affected_component"] == "training_loop"
    assert trace["hypothesis"]["hypothesis"] == "If dropout is increased, then generalization will improve"
    assert trace["hypothesis"]["mechanism"] == "stronger regularization reduces co-adaptation"
    assert trace["hypothesis"]["expected_improvement"] == "+2-3% accuracy"
    assert trace["hypothesis"]["testable_prediction"] == "smaller train/val gap"
    assert trace["design"]["summary"] == "Increase dropout from 0.2 to 0.4 and compare validation accuracy"
    assert trace["design"]["constraints"] == ["possible underfitting"]
    assert trace["design"]["virtual_score"] == 0.68
    assert trace["design"]["implementation_steps"] == [
        "Update model config",
        "Run 3 seeds",
        "Compare metrics",
    ]


def test_pipeline_llm_error_propagates() -> None:
    adapter = LLMAdapter(AlwaysInvalidJSONProvider(), config=LLMAdapterConfig(max_retries=0))
    pipeline = ReasoningPipeline(adapter)

    with pytest.raises(ValueError):
        pipeline.reason(
            task_summary="Any task",
            scenario_name="test",
            iteration=0,
            previous_results=[],
            current_scores=[],
        )


def test_pipeline_partial_json_is_rejected() -> None:
    adapter = LLMAdapter(MissingRequiredFieldsProvider(), config=LLMAdapterConfig(max_retries=0))
    pipeline = ReasoningPipeline(adapter)

    with pytest.raises(ValueError):
        pipeline.reason(
            task_summary="Any task",
            scenario_name="test",
            iteration=0,
            previous_results=[],
            current_scores=[],
        )


def test_pipeline_provider_disconnect_retries_and_recovers() -> None:
    provider = SequencedProvider(
        [
            ConnectionError("provider socket closed"),
            '{"strengths":["s1"],"weaknesses":["w1"],"current_performance":"stable","key_observations":"obs"}',
            '{"problem":"p1","severity":"high","evidence":"e1","affected_component":"optimizer"}',
            '{"hypothesis":"h1","mechanism":"m1","expected_improvement":"+3%","testable_prediction":"tp1"}',
            '{"summary":"exp design","constraints":["c1"],"virtual_score":0.8,"implementation_steps":["step1"]}',
        ]
    )
    pipeline = ReasoningPipeline(LLMAdapter(provider, config=LLMAdapterConfig(max_retries=1)))

    result = pipeline.reason(
        task_summary="Recover from transient provider disconnect",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )

    assert isinstance(result, ExperimentDesign)
    assert result.summary == "exp design"
    assert provider.calls > 4


def test_pipeline_non_object_payload_exposes_payload_type_diagnostics() -> None:
    adapter = LLMAdapter(
        SequencedProvider(['["not","an","object"]']),
        config=LLMAdapterConfig(max_retries=0),
    )
    pipeline = ReasoningPipeline(adapter)

    with pytest.raises(StructuredOutputParseError) as ctx:
        pipeline.reason(
            task_summary="Any task",
            scenario_name="test",
            iteration=0,
            previous_results=[],
            current_scores=[],
        )

    assert ctx.value.failure_counts == {"payload_type": 1}
    assert ctx.value.failure_stages == ("payload_type",)


def test_trace_store_receives_trace() -> None:
    trace_store = RecordingTraceStore()
    pipeline = ReasoningPipeline(LLMAdapter(MockLLMProvider()), trace_store=trace_store)

    result = pipeline.reason(
        task_summary="Improve baseline accuracy",
        scenario_name="data_science",
        iteration=1,
        previous_results=["Run 0 reached 0.71 accuracy"],
        current_scores=[0.71],
    )

    assert isinstance(result, ExperimentDesign)
    assert trace_store.calls == 1
    assert len(trace_store.records) == 1
    stored_trace = trace_store.records[0]
    assert isinstance(stored_trace, ReasoningTrace)
    assert stored_trace.trace_id
    assert set(stored_trace.stages.keys()) == {"analysis", "problem", "hypothesis", "design"}
    assert stored_trace.timestamp
    assert stored_trace.metadata


def test_trace_store_none_backward_compatible() -> None:
    pipeline = ReasoningPipeline(LLMAdapter(MockLLMProvider()))

    result = pipeline.reason(
        task_summary="Improve baseline accuracy",
        scenario_name="data_science",
        iteration=1,
        previous_results=["Run 0 reached 0.71 accuracy"],
        current_scores=[0.71],
    )

    assert isinstance(result, ExperimentDesign)
    assert result.summary
    assert result.implementation_steps


def test_trace_store_metadata_contains_context() -> None:
    trace_store = RecordingTraceStore()
    pipeline = ReasoningPipeline(LLMAdapter(MockLLMProvider()), trace_store=trace_store)

    pipeline.reason(
        task_summary="test_task",
        scenario_name="data_science",
        iteration=5,
        previous_results=["Run 4 reached 0.79 accuracy"],
        current_scores=[0.79],
    )

    stored_trace = trace_store.records[0]
    assert stored_trace.metadata == {
        "task_summary": "test_task",
        "scenario": "data_science",
        "iteration": "5",
    }
