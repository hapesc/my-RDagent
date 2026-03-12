"""P0: Single-round code generation quality evaluation.

Runs each code-type golden task through the LLM, then evaluates the generated
artifact with DeepEval G-Eval for functional correctness.

Requires: --run-evals flag + a valid LLM API key.
"""

from __future__ import annotations

import pytest
from deepeval import assert_test

from evaluation_service.custom_metrics.code_quality import create_code_correctness_metric
from evaluation_service.deepeval_bridge import golden_task_to_test_case
from llm import LLMAdapter
from service_contracts import ModelSelectorConfig
from tests.golden_tasks.benchmark import (
    BenchmarkResult,
    load_golden_tasks,
    run_single_round,
)

pytestmark = pytest.mark.eval

# Only code-type tasks (quant, data_science) — synthetic_research is P3
_CODE_TASKS = [t for t in load_golden_tasks() if t["artifact_type"] == "code"]


def test_deepeval_importable():
    import deepeval

    assert hasattr(deepeval, "__version__")


def test_code_correctness_metric_instantiable():
    try:
        metric = create_code_correctness_metric(scenario="quant")
    except Exception as exc:
        if "API key" in str(exc):
            pytest.skip("OpenAI API key not configured")
        raise
    assert metric.name == "Code Correctness (quant)"
    assert metric.threshold == 0.7


def test_bridge_golden_task_to_test_case():
    task = {
        "task_id": "quant_momentum",
        "scenario": "quant",
        "task_summary": "Implement a 5-day price momentum factor.",
        "artifact_type": "code",
        "expected_properties": {"compiles": True, "has_signature": "compute_factor"},
    }
    actual_output = "def compute_factor(df): return df"
    tc = golden_task_to_test_case(task, actual_output)
    assert tc.input == task["task_summary"]
    assert tc.actual_output == actual_output
    assert tc.context is not None


@pytest.fixture(scope="module")
def codegen_results(
    eval_llm_adapter: LLMAdapter,
    eval_model_config: ModelSelectorConfig,
) -> dict[str, BenchmarkResult]:
    """Run each code-type golden task once and cache results for the module."""
    results: dict[str, BenchmarkResult] = {}
    for task in _CODE_TASKS:
        result = run_single_round(task, eval_llm_adapter, eval_model_config)
        results[task["task_id"]] = result
    return results


@pytest.mark.parametrize("task", _CODE_TASKS, ids=lambda t: t["task_id"])
def test_codegen_structural_pass(
    task: dict,
    codegen_results: dict[str, BenchmarkResult],
) -> None:
    """Verify that generated code passes existing structural checks (QualityGate)."""
    result = codegen_results[task["task_id"]]
    if not result.passed:
        pytest.fail(f"Structural check failed: {result.reasons}")


@pytest.mark.parametrize("task", _CODE_TASKS, ids=lambda t: t["task_id"])
def test_codegen_functional_correctness(
    task: dict,
    codegen_results: dict[str, BenchmarkResult],
) -> None:
    """G-Eval: functional correctness of generated code."""
    result = codegen_results[task["task_id"]]
    if not result.artifact:
        pytest.skip("No artifact generated — structural check failed")

    test_case = golden_task_to_test_case(task, result.artifact)
    metric = create_code_correctness_metric(scenario=task["scenario"])
    assert_test(test_case, [metric])
