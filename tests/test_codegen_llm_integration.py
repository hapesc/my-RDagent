from __future__ import annotations

import pytest

from tests.golden_tasks.benchmark import load_golden_tasks, run_single_round

pytestmark = pytest.mark.llm


@pytest.mark.parametrize("golden_task", load_golden_tasks(), ids=lambda task: task["task_id"])
def test_single_round_codegen_produces_non_empty_artifact(
    golden_task,
    benchmark_llm_adapter,
    benchmark_model_config,
) -> None:
    result = run_single_round(golden_task, benchmark_llm_adapter, benchmark_model_config)
    assert result.artifact.strip(), f"{golden_task['task_id']} produced an empty artifact"
