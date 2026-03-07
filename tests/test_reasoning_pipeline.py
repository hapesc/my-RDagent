from __future__ import annotations

import pytest

from core.reasoning.pipeline import ReasoningPipeline
from llm.adapter import LLMAdapter, LLMAdapterConfig, MockLLMProvider
from llm.schemas import (
    AnalysisResult,
    ExperimentDesign,
    HypothesisFormulation,
    ProblemIdentification,
)
from service_contracts import ModelSelectorConfig


class CountingMockLLMProvider(MockLLMProvider):
    def __init__(self, responses=None) -> None:
        super().__init__(responses=responses)
        self.call_count = 0
        self.model_configs = []

    def complete(self, prompt: str, model_config=None) -> str:
        self.call_count += 1
        self.model_configs.append(model_config)
        return super().complete(prompt, model_config=model_config)


def _build_pipeline(provider: MockLLMProvider, max_retries: int = 2) -> ReasoningPipeline:
    adapter = LLMAdapter(provider, config=LLMAdapterConfig(max_retries=max_retries))
    return ReasoningPipeline(adapter)


def test_pipeline_instantiation_with_mock_adapter() -> None:
    pipeline = _build_pipeline(MockLLMProvider())
    assert isinstance(pipeline, ReasoningPipeline)


def test_reason_returns_experiment_design_with_non_empty_fields() -> None:
    pipeline = _build_pipeline(MockLLMProvider())

    design = pipeline.reason(
        task_summary="Improve baseline model performance",
        scenario_name="data_science",
        iteration=1,
        previous_results=["baseline score 0.72"],
        current_scores=[0.72],
    )

    assert isinstance(design, ExperimentDesign)
    assert design.summary.strip() != ""
    assert isinstance(design.implementation_steps, list)
    assert len(design.implementation_steps) > 0


def test_reason_calls_llm_adapter_exactly_four_times() -> None:
    provider = CountingMockLLMProvider()
    pipeline = _build_pipeline(provider)

    _ = pipeline.reason(
        task_summary="Tune optimizer",
        scenario_name="data_science",
        iteration=2,
        previous_results=["sgd underfits"],
        current_scores=[0.65],
    )

    assert provider.call_count == 4


def test_reason_with_trace_returns_design_and_trace_dict() -> None:
    pipeline = _build_pipeline(MockLLMProvider())

    design, trace = pipeline.reason_with_trace(
        task_summary="Optimize learning rate schedule",
        scenario_name="data_science",
        iteration=3,
        previous_results=["lr=1e-3 unstable", "lr=5e-4 stable but slow"],
        current_scores=[0.68, 0.71],
    )

    assert isinstance(design, ExperimentDesign)
    assert isinstance(trace, dict)


def test_build_reasoning_trace_top_level_keys_exact_match() -> None:
    analysis = AnalysisResult.from_dict(
        {
            "strengths": ["s1"],
            "weaknesses": ["w1"],
            "current_performance": "flat",
            "key_observations": "obs",
        }
    )
    problem = ProblemIdentification.from_dict(
        {
            "problem": "p",
            "severity": "high",
            "evidence": "e",
            "affected_component": "trainer",
        }
    )
    hypothesis = HypothesisFormulation.from_dict(
        {
            "hypothesis": "h",
            "mechanism": "m",
            "expected_improvement": "+3%",
            "testable_prediction": "tp",
        }
    )
    design = ExperimentDesign.from_dict(
        {
            "summary": "d",
            "constraints": ["c"],
            "virtual_score": 0.8,
            "implementation_steps": ["step"],
        }
    )

    trace = ReasoningPipeline._build_reasoning_trace(analysis, problem, hypothesis, design)
    assert set(trace.keys()) == {"analysis", "problem", "hypothesis", "design"}


def test_build_reasoning_trace_subdict_keys_match_schema_fields() -> None:
    trace = ReasoningPipeline._build_reasoning_trace(
        AnalysisResult.from_dict({}),
        ProblemIdentification.from_dict({}),
        HypothesisFormulation.from_dict({}),
        ExperimentDesign.from_dict({}),
    )

    assert set(trace["analysis"].keys()) == {
        "strengths",
        "weaknesses",
        "current_performance",
        "key_observations",
    }
    assert set(trace["problem"].keys()) == {
        "problem",
        "severity",
        "evidence",
        "affected_component",
    }
    assert set(trace["hypothesis"].keys()) == {
        "hypothesis",
        "mechanism",
        "expected_improvement",
        "testable_prediction",
    }
    assert set(trace["design"].keys()) == {
        "summary",
        "constraints",
        "virtual_score",
        "implementation_steps",
    }


def test_reason_propagates_value_error_from_adapter() -> None:
    provider = MockLLMProvider(responses=["not-json"])
    pipeline = _build_pipeline(provider, max_retries=0)

    with pytest.raises(ValueError):
        pipeline.reason(
            task_summary="Any task",
            scenario_name="data_science",
            iteration=1,
            previous_results=["r1"],
            current_scores=[0.1],
        )


def test_reason_accepts_model_config_and_forwards_to_all_calls() -> None:
    provider = CountingMockLLMProvider()
    pipeline = _build_pipeline(provider)
    model_config = ModelSelectorConfig(provider="mock", model="gpt-test", temperature=0.2)

    design = pipeline.reason(
        task_summary="Improve recall",
        scenario_name="data_science",
        iteration=1,
        previous_results=["run-1"],
        current_scores=[0.42],
        model_config=model_config,
    )

    assert isinstance(design, ExperimentDesign)
    assert provider.call_count == 4
    assert provider.model_configs == [model_config, model_config, model_config, model_config]


def test_reason_works_with_history_lists() -> None:
    pipeline = _build_pipeline(MockLLMProvider())

    design = pipeline.reason(
        task_summary="Improve convergence speed",
        scenario_name="data_science",
        iteration=4,
        previous_results=[
            "iter1: baseline",
            "iter2: +dropout",
            "iter3: +scheduler",
            "iter4: +augmentation",
        ],
        current_scores=[0.61, 0.67, 0.69, 0.705],
    )

    assert isinstance(design, ExperimentDesign)
    assert design.summary != ""


def test_reason_handles_empty_inputs_iteration_zero() -> None:
    pipeline = _build_pipeline(MockLLMProvider())

    design = pipeline.reason(
        task_summary="",
        scenario_name="",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )

    assert isinstance(design, ExperimentDesign)
    assert isinstance(design.summary, str)
    assert isinstance(design.implementation_steps, list)
