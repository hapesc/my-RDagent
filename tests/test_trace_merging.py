import json
import importlib

import pytest

from llm.adapter import LLMAdapter, MockLLMProvider
from llm.prompts import merge_traces_prompt
from llm.schemas import ExperimentDesign

TraceMerger = importlib.import_module("exploration_manager.merging").TraceMerger


def _make_merger():
    adapter = LLMAdapter(MockLLMProvider())
    return TraceMerger(adapter)


def _sample_traces():
    return [
        {
            "analysis": {"key_observations": "good feature eng"},
            "problem": {"problem": "overfitting"},
            "hypothesis": {"hypothesis": "regularize"},
            "design": {
                "summary": "add L2",
                "constraints": ["c1"],
                "virtual_score": 0.7,
                "implementation_steps": ["step1"],
            },
        },
        {
            "analysis": {"key_observations": "fast convergence"},
            "problem": {"problem": "low recall"},
            "hypothesis": {"hypothesis": "class weights"},
            "design": {
                "summary": "weighted loss",
                "constraints": ["c2"],
                "virtual_score": 0.6,
                "implementation_steps": ["step2"],
            },
        },
    ]


def test_empty_traces_raises_value_error():
    merger = _make_merger()
    with pytest.raises(ValueError):
        merger.merge([], "task", "scenario")


def test_single_trace_returns_design_without_llm_call():
    traces = _sample_traces()[:1]
    merger = _make_merger()
    result = merger.merge(traces, "task", "scenario")
    assert isinstance(result, ExperimentDesign)
    assert result.summary == "add L2"
    assert result.implementation_steps == ["step1"]


def test_multiple_traces_calls_llm_and_returns_merged_design():
    traces = _sample_traces() + [
        {
            "analysis": {"key_observations": "better calibration"},
            "problem": {"problem": "precision drops"},
            "hypothesis": {"hypothesis": "temperature scaling"},
            "design": {
                "summary": "post-hoc calibration",
                "constraints": ["c3"],
                "virtual_score": 0.65,
                "implementation_steps": ["step3"],
            },
        }
    ]
    merger = _make_merger()
    result = merger.merge(traces, "improve classifier", "data_science")
    assert isinstance(result, ExperimentDesign)
    assert result.summary == "Merged experiment design"


def test_merged_design_has_non_empty_summary():
    merger = _make_merger()
    result = merger.merge(_sample_traces(), "task", "scenario")
    assert isinstance(result.summary, str)
    assert result.summary.strip() != ""


def test_merged_design_has_implementation_steps():
    merger = _make_merger()
    result = merger.merge(_sample_traces(), "task", "scenario")
    assert isinstance(result.implementation_steps, list)
    assert len(result.implementation_steps) > 0


def test_format_trace_handles_dict_traces():
    trace = _sample_traces()[0]
    text = TraceMerger._format_trace(trace, 0)
    assert "Analysis: good feature eng" in text
    assert "Problem: overfitting" in text
    assert "Hypothesis: regularize" in text
    assert "Design: add L2" in text


def test_format_trace_handles_string_values():
    trace = {
        "analysis": "plain analysis",
        "problem": "plain problem",
        "hypothesis": "plain hypothesis",
        "design": "plain design",
    }
    text = TraceMerger._format_trace(trace, 1)
    assert "Analysis: plain analysis" in text
    assert "Problem: plain problem" in text
    assert "Hypothesis: plain hypothesis" in text
    assert "Design: plain design" in text


def test_merge_traces_prompt_produces_expected_sections():
    trace_summaries = ["trace A summary", "trace B summary"]
    prompt = merge_traces_prompt(
        trace_summaries=trace_summaries,
        task_summary="Build robust model",
        scenario_name="data_science",
    )
    assert "research synthesizer" in prompt
    assert "Build robust model" in prompt
    assert "### Trace 1" in prompt
    assert "### Trace 2" in prompt
    assert "## Output Fields" in prompt
    assert "`implementation_steps`" in prompt


def test_mock_llm_provider_detects_merge_prompt():
    provider = MockLLMProvider()
    raw = provider.complete(
        "You are an expert research synthesizer.\n## Completed Traces\n..."
    )
    payload = json.loads(raw)
    assert payload["summary"] == "Merged experiment design"
    assert "implementation_steps" in payload
