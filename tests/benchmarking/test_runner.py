from __future__ import annotations

from unittest.mock import patch

from benchmarking.reporting import run_result_to_json_dict, summarize_run_markdown
from benchmarking.result_schema import FailureBucket
from benchmarking.runner import run_benchmark


def test_runner_executes_tasks_and_returns_run_result() -> None:
    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-1",
                task_summary="smoke task",
                source_type="local_fixture",
                inputs={"prompt": "hello"},
                reference_outputs={"answer": "world"},
                tags=("smoke",),
            )
        ]

    def fake_runtime_target(task):
        _ = task
        return {
            "status": "COMPLETED",
            "outputs": {"artifact": "ok"},
            "timing": {"duration_sec": 1.2},
            "artifact_refs": {"report": "artifacts/report.md"},
            "runtime": {
                "llm_provider": "litellm",
                "llm_model": "gpt-4.1-mini",
                "judge_model": "gpt-4.1-mini",
            },
        }

    def structural_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        return {"passed": True}

    def scenario_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        return {"score": 0.9, "metrics": {"accuracy": 0.9}}

    def judge_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        return {"score": 0.85}

    result = run_benchmark(
        run_id="run-bench-1",
        profile_name="smoke",
        scenario="data_science",
        runtime_target=fake_runtime_target,
        task_materializer=fake_task_materializer,
        structural_evaluators=[structural_evaluator],
        scenario_evaluator=scenario_evaluator,
        judge_evaluators={"faithfulness": judge_evaluator},
    )

    assert result.run_id == "run-bench-1"
    assert len(result.case_results) == 1
    case = result.case_results[0]
    assert case.failure_bucket == FailureBucket.SUCCESS
    assert case.scenario_score == 0.9
    assert case.judge_scores["faithfulness"] == 0.85


def test_runner_classifies_structural_failures() -> None:
    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-structural",
                task_summary="structural fail",
                source_type="local_fixture",
            )
        ]

    def fake_runtime_target(task):
        _ = task
        return {
            "status": "COMPLETED",
            "outputs": {},
            "runtime": {
                "llm_provider": "litellm",
                "llm_model": "gpt-4.1-mini",
                "judge_model": None,
            },
        }

    def structural_fail(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        return {"passed": False, "reason": "missing key"}

    result = run_benchmark(
        run_id="run-bench-2",
        profile_name="smoke",
        scenario="data_science",
        runtime_target=fake_runtime_target,
        task_materializer=fake_task_materializer,
        structural_evaluators=[structural_fail],
        scenario_evaluator=None,
        judge_evaluators={},
    )

    assert result.case_results[0].failure_bucket == FailureBucket.STRUCTURAL_FAILURE


def test_runner_skips_scenario_and_judge_after_structural_failure() -> None:
    calls = {"scenario": 0, "judge": 0}

    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-skip",
                task_summary="skip downstream evaluators",
                source_type="local_fixture",
            )
        ]

    def fake_runtime_target(task):
        _ = task
        return {
            "status": "COMPLETED",
            "outputs": {},
            "runtime": {"llm_provider": "litellm", "llm_model": "gpt-4.1-mini", "judge_model": None},
        }

    def structural_fail(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        return {"passed": False}

    def scenario_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        calls["scenario"] += 1
        return {"score": 1.0, "metrics": {}}

    def judge_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        calls["judge"] += 1
        return {"score": 1.0}

    result = run_benchmark(
        run_id="run-bench-skip",
        profile_name="smoke",
        scenario="data_science",
        runtime_target=fake_runtime_target,
        task_materializer=fake_task_materializer,
        structural_evaluators=[structural_fail],
        scenario_evaluator=scenario_evaluator,
        judge_evaluators={"faithfulness": judge_evaluator},
    )

    assert result.case_results[0].failure_bucket == FailureBucket.STRUCTURAL_FAILURE
    assert calls == {"scenario": 0, "judge": 0}


def test_runner_classifies_runtime_and_judge_failures() -> None:
    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-runtime-failure",
                task_summary="runtime failure",
                source_type="local_fixture",
            ),
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-judge-failure",
                task_summary="judge failure",
                source_type="local_fixture",
            ),
        ]

    def fake_runtime_target(task):
        if task.task_id == "task-runtime-failure":
            return {"status": "FAILED", "outputs": {}, "runtime": {}}
        return {
            "status": "COMPLETED",
            "outputs": {},
            "runtime": {"llm_provider": "litellm", "llm_model": "gpt-4.1-mini", "judge_model": None},
        }

    def judge_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        raise RuntimeError("judge failure")

    result = run_benchmark(
        run_id="run-bench-failures",
        profile_name="smoke",
        scenario="data_science",
        runtime_target=fake_runtime_target,
        task_materializer=fake_task_materializer,
        structural_evaluators=[],
        scenario_evaluator=None,
        judge_evaluators={"faithfulness": judge_evaluator},
    )

    assert result.case_results[0].failure_bucket == FailureBucket.GENERATION_FAILURE
    assert result.case_results[1].failure_bucket == FailureBucket.JUDGE_FAILURE


def test_runner_classifies_structural_evaluator_exceptions_as_structural_failure() -> None:
    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-structural-exception",
                task_summary="structural exception",
                source_type="local_fixture",
            )
        ]

    def fake_runtime_target(task):
        _ = task
        return {"status": "COMPLETED", "outputs": {}, "runtime": {}}

    def structural_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        raise RuntimeError("broken rule")

    result = run_benchmark(
        run_id="run-bench-structural-exception",
        profile_name="smoke",
        scenario="data_science",
        runtime_target=fake_runtime_target,
        task_materializer=fake_task_materializer,
        structural_evaluators=[structural_evaluator],
        scenario_evaluator=None,
        judge_evaluators={},
    )

    assert result.case_results[0].failure_bucket == FailureBucket.STRUCTURAL_FAILURE


def test_runner_classifies_unknown_runtime_status_as_infra_failure() -> None:
    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-unknown-status",
                task_summary="unknown runtime status",
                source_type="local_fixture",
            )
        ]

    def fake_runtime_target(task):
        _ = task
        return {"status": "MYSTERY_STATUS", "outputs": {}, "runtime": {}}

    result = run_benchmark(
        run_id="run-bench-unknown-status",
        profile_name="smoke",
        scenario="data_science",
        runtime_target=fake_runtime_target,
        task_materializer=fake_task_materializer,
        structural_evaluators=[],
        scenario_evaluator=None,
        judge_evaluators={},
    )

    assert result.case_results[0].failure_bucket == FailureBucket.INFRA_FAILURE


def test_runner_uses_profile_enabled_layers_to_skip_evaluators() -> None:
    calls = {"rules": 0, "scenario": 0, "judge": 0}

    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-layer-skip",
                task_summary="layer skip",
                source_type="local_fixture",
            )
        ]

    def fake_runtime_target(task):
        _ = task
        return {"status": "COMPLETED", "outputs": {}, "runtime": {}}

    def structural_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        calls["rules"] += 1
        return {"passed": True}

    def scenario_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        calls["scenario"] += 1
        return {"score": 1.0, "metrics": {}}

    def judge_evaluator(*, inputs, outputs, reference_outputs):
        _ = (inputs, outputs, reference_outputs)
        calls["judge"] += 1
        return {"score": 1.0}

    with patch("benchmarking.runner.get_profile") as mock_get_profile:
        mock_get_profile.return_value = type(
            "Profile",
            (),
            {"enabled_layers": ("rules",), "rerun_count": 1},
        )()
        run_benchmark(
            run_id="run-bench-layer-skip",
            profile_name="smoke",
            scenario="data_science",
            runtime_target=fake_runtime_target,
            task_materializer=fake_task_materializer,
            structural_evaluators=[structural_evaluator],
            scenario_evaluator=scenario_evaluator,
            judge_evaluators={"faithfulness": judge_evaluator},
        )

    assert calls == {"rules": 1, "scenario": 0, "judge": 0}


def test_runner_retries_runtime_target_per_profile_rerun_count() -> None:
    calls = {"runtime": 0}

    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-rerun",
                task_summary="rerun",
                source_type="local_fixture",
            )
        ]

    def fake_runtime_target(task):
        _ = task
        calls["runtime"] += 1
        return {"status": "COMPLETED", "outputs": {}, "runtime": {}}

    with patch("benchmarking.runner.get_profile") as mock_get_profile:
        mock_get_profile.return_value = type(
            "Profile",
            (),
            {"enabled_layers": ("rules", "scenario", "judge"), "rerun_count": 3},
        )()
        run_benchmark(
            run_id="run-bench-rerun",
            profile_name="daily",
            scenario="data_science",
            runtime_target=fake_runtime_target,
            task_materializer=fake_task_materializer,
            structural_evaluators=[],
            scenario_evaluator=None,
            judge_evaluators={},
        )

    assert calls["runtime"] == 3


def test_runner_classifies_running_status_as_generation_failure() -> None:
    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-running-status",
                task_summary="running status",
                source_type="local_fixture",
            )
        ]

    def fake_runtime_target(task):
        _ = task
        return {"status": "RUNNING", "outputs": {}, "runtime": {}}

    result = run_benchmark(
        run_id="run-bench-running-status",
        profile_name="smoke",
        scenario="data_science",
        runtime_target=fake_runtime_target,
        task_materializer=fake_task_materializer,
        structural_evaluators=[],
        scenario_evaluator=None,
        judge_evaluators={},
    )

    assert result.case_results[0].failure_bucket == FailureBucket.GENERATION_FAILURE


def test_reporting_helpers_emit_json_and_markdown() -> None:
    def fake_task_materializer(profile: str, scenario: str | None):
        from benchmarking.contracts import BenchmarkTask

        _ = profile
        return [
            BenchmarkTask(
                scenario=scenario or "data_science",
                task_id="task-report",
                task_summary="report task",
                source_type="local_fixture",
            )
        ]

    def fake_runtime_target(task):
        _ = task
        return {
            "status": "COMPLETED",
            "outputs": {},
            "runtime": {
                "llm_provider": "litellm",
                "llm_model": "gpt-4.1-mini",
                "judge_model": None,
            },
        }

    result = run_benchmark(
        run_id="run-bench-3",
        profile_name="smoke",
        scenario="data_science",
        runtime_target=fake_runtime_target,
        task_materializer=fake_task_materializer,
        structural_evaluators=[],
        scenario_evaluator=None,
        judge_evaluators={},
    )

    payload = run_result_to_json_dict(result)
    markdown = summarize_run_markdown(result)

    assert payload["run_id"] == "run-bench-3"
    assert "case_results" in payload
    assert "run-bench-3" in markdown
    assert "Success cases" in markdown
