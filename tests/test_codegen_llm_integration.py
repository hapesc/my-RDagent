from __future__ import annotations

import pytest

from tests.golden_tasks.benchmark import load_golden_tasks, run_single_round

pytestmark = pytest.mark.llm


@pytest.fixture(scope="session")
def benchmark_results(benchmark_llm_adapter, benchmark_model_config):
    tasks = load_golden_tasks()
    return {task["task_id"]: run_single_round(task, benchmark_llm_adapter, benchmark_model_config) for task in tasks}


@pytest.mark.parametrize("golden_task", load_golden_tasks(), ids=lambda task: task["task_id"])
def test_single_round_codegen_passes_quality_gate(golden_task, benchmark_results) -> None:
    result = benchmark_results[golden_task["task_id"]]
    assert result.passed, f"{golden_task['task_id']} failed: {result.reasons}"


def test_aggregate_pass_rate_above_80_percent(benchmark_results) -> None:
    results = list(benchmark_results.values())
    passed = sum(1 for result in results if result.passed)
    rate = passed / len(results)
    assert rate >= 0.8, f"aggregate pass rate {rate:.0%} ({passed}/{len(results)}) below 80%"


@pytest.mark.parametrize("scenario", ["quant", "data_science", "synthetic_research"])
def test_per_scenario_pass_rate_above_60_percent(scenario, benchmark_results) -> None:
    tasks = load_golden_tasks(scenario=scenario)
    assert len(tasks) >= 2
    results = [benchmark_results[task["task_id"]] for task in tasks]
    passed = sum(1 for result in results if result.passed)
    rate = passed / len(results)
    assert rate >= 0.6, f"{scenario} pass rate {rate:.0%} ({passed}/{len(results)}) below 60%"
