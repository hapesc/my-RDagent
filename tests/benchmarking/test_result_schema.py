from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import asdict
from typing import get_type_hints
from unittest.mock import patch

from benchmarking.contracts import (
    BenchmarkRunConfig,
    BenchmarkTask,
    JudgeEvaluator,
    ScenarioEvaluator,
    TraceRecorder,
)
from benchmarking.result_schema import BenchmarkCaseResult, BenchmarkRunResult, FailureBucket


def test_benchmark_dependency_langsmith_is_available() -> None:
    assert importlib.util.find_spec("langsmith") is not None


def test_benchmark_dependency_langchain_openai_is_available() -> None:
    assert importlib.util.find_spec("langchain_openai") is not None


def test_eval_collection_gate_only_ignores_legacy_evals_without_deepeval() -> None:
    sys.modules.pop("tests.conftest", None)
    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str):
        if name == "deepeval":
            return None
        return original_find_spec(name)

    with patch("importlib.util.find_spec", side_effect=fake_find_spec):
        module = importlib.import_module("tests.conftest")

    assert getattr(module, "collect_ignore_glob", []) == ["evals/*"]


def test_schema_failure_bucket_contains_expected_values() -> None:
    assert [member.value for member in FailureBucket] == [
        "infra_failure",
        "generation_failure",
        "artifact_missing",
        "structural_failure",
        "scenario_eval_failure",
        "judge_failure",
        "quality_failure",
        "success",
    ]


def test_schema_benchmark_case_result_fields() -> None:
    hints = get_type_hints(BenchmarkCaseResult)
    assert set(hints) == {
        "scenario",
        "task_id",
        "profile",
        "agent_status",
        "llm_provider",
        "llm_model",
        "judge_model",
        "failure_bucket",
        "scenario_score",
        "scenario_metrics",
        "judge_scores",
        "timing",
        "artifact_refs",
    }


def test_schema_run_result_is_dataclass_serializable() -> None:
    case = BenchmarkCaseResult(
        scenario="data_science",
        task_id="t-1",
        profile="smoke",
        agent_status="completed",
        llm_provider="litellm",
        llm_model="gpt-4.1-mini",
        judge_model="gpt-4.1-mini",
        failure_bucket=FailureBucket.SUCCESS,
        scenario_score=0.9,
        scenario_metrics={"accuracy": 0.9},
        judge_scores={"faithfulness": 0.8},
        timing={"duration_sec": 1.23},
        artifact_refs={"report": "artifacts/report.md"},
    )
    run = BenchmarkRunResult(
        run_id="run-1",
        profile="smoke",
        scenario="data_science",
        case_results=[case],
        summary={"pass_rate": 1.0},
    )
    payload = asdict(run)
    assert payload["run_id"] == "run-1"
    assert payload["case_results"][0]["failure_bucket"] == "success"


def test_contract_benchmark_task_and_run_config_dataclasses() -> None:
    task = BenchmarkTask(
        scenario="data_science",
        task_id="task-1",
        task_summary="test task",
        source_type="local_fixture",
        inputs={"prompt": "x"},
        reference_outputs={"answer": "y"},
        tags=("smoke",),
    )
    config = BenchmarkRunConfig(
        profile="smoke",
        scenarios=("data_science",),
        upload_results=False,
        rerun_count=1,
        enabled_layers=("rules", "scenario", "judge"),
    )
    assert task.task_id == "task-1"
    assert config.profile == "smoke"


def test_contract_protocol_types_exist() -> None:
    assert isinstance(JudgeEvaluator, type)
    assert isinstance(ScenarioEvaluator, type)
    assert isinstance(TraceRecorder, type)
