"""P3: Synthetic research report quality evaluation."""

from __future__ import annotations

import pytest
from deepeval import assert_test

from evaluation_service.custom_metrics.report_quality import (
    create_report_coherence_metric,
    create_report_depth_metric,
    create_report_faithfulness_metric,
)
from evaluation_service.deepeval_bridge import report_to_test_case
from llm import LLMAdapter
from service_contracts import ModelSelectorConfig
from tests.golden_tasks.benchmark import load_golden_tasks, run_single_round

pytestmark = pytest.mark.eval


def test_report_metrics_instantiable():
    try:
        depth = create_report_depth_metric()
        coherence = create_report_coherence_metric()
        faithfulness = create_report_faithfulness_metric()
    except Exception as exc:
        if "API key" in str(exc):
            pytest.skip("OpenAI API key not configured")
        raise
    assert "Depth" in depth.name
    assert "Coherence" in coherence.name
    assert "Faithfulness" in faithfulness.name


_REPORT_TASKS = [t for t in load_golden_tasks() if t["artifact_type"] == "structured_text"]


@pytest.fixture(scope="module")
def report_results(
    eval_llm_adapter: LLMAdapter,
    eval_model_config: ModelSelectorConfig,
) -> dict[str, str]:
    """Generate reports for each synthetic golden task."""
    results: dict[str, str] = {}
    for task in _REPORT_TASKS:
        result = run_single_round(task, eval_llm_adapter, eval_model_config)
        results[task["task_id"]] = result.artifact
    return results


@pytest.mark.parametrize("task", _REPORT_TASKS, ids=lambda t: t["task_id"])
def test_report_depth(
    task: dict,
    report_results: dict[str, str],
) -> None:
    """G-Eval: report analytical depth."""
    artifact = report_results[task["task_id"]]
    if not artifact:
        pytest.skip("No report generated")
    tc = report_to_test_case(task["task_summary"], artifact)
    assert_test(tc, [create_report_depth_metric()])


@pytest.mark.parametrize("task", _REPORT_TASKS, ids=lambda t: t["task_id"])
def test_report_coherence(
    task: dict,
    report_results: dict[str, str],
) -> None:
    """G-Eval: report logical coherence."""
    artifact = report_results[task["task_id"]]
    if not artifact:
        pytest.skip("No report generated")
    tc = report_to_test_case(task["task_summary"], artifact)
    assert_test(tc, [create_report_coherence_metric()])
