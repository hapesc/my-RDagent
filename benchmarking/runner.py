"""Synchronous benchmark runner."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from benchmarking.profiles import get_profile
from benchmarking.reporting import run_result_to_json_dict
from benchmarking.result_schema import BenchmarkCaseResult, BenchmarkRunResult, FailureBucket
from benchmarking.task_registry import materialize_tasks


RuntimeTarget = Callable[[Any], dict[str, Any]]


def run_benchmark(
    *,
    run_id: str,
    profile_name: str,
    scenario: str | None,
    runtime_target: RuntimeTarget,
    task_materializer=materialize_tasks,
    structural_evaluators: list | None = None,
    scenario_evaluator=None,
    judge_evaluators: dict | None = None,
) -> BenchmarkRunResult:
    profile = get_profile(profile_name)
    tasks = task_materializer(profile_name, scenario)
    case_results: list[BenchmarkCaseResult] = []

    for task in tasks:
        runtime_result = _run_with_profile_retries(runtime_target, task, profile.rerun_count)
        outputs = dict(runtime_result.get("outputs", {}))
        runtime_meta = dict(runtime_result.get("runtime", {}))
        failure_bucket = _classify_runtime_status(runtime_result)

        structural_failure = False
        if failure_bucket == FailureBucket.SUCCESS and "rules" in profile.enabled_layers:
            for evaluator in structural_evaluators or []:
                try:
                    evaluation = evaluator(
                        inputs=task.inputs,
                        outputs=outputs,
                        reference_outputs=task.reference_outputs,
                    )
                except Exception:
                    structural_failure = True
                    failure_bucket = FailureBucket.STRUCTURAL_FAILURE
                    break
                else:
                    if not evaluation.get("passed", False):
                        structural_failure = True
                        failure_bucket = FailureBucket.STRUCTURAL_FAILURE
                        break

        scenario_score = None
        scenario_metrics = {}
        if failure_bucket == FailureBucket.SUCCESS and scenario_evaluator is not None and "scenario" in profile.enabled_layers:
            try:
                scenario_result = scenario_evaluator(
                    inputs=task.inputs,
                    outputs=outputs,
                    reference_outputs=task.reference_outputs,
                )
            except Exception:
                failure_bucket = FailureBucket.SCENARIO_EVAL_FAILURE
            else:
                scenario_score = scenario_result.get("score")
                scenario_metrics = dict(scenario_result.get("metrics", {}))

        judge_scores = {}
        if failure_bucket == FailureBucket.SUCCESS and "judge" in profile.enabled_layers:
            for name, evaluator in (judge_evaluators or {}).items():
                try:
                    judge_result = evaluator(
                        inputs=task.inputs,
                        outputs=outputs,
                        reference_outputs=task.reference_outputs,
                    )
                except Exception:
                    failure_bucket = FailureBucket.JUDGE_FAILURE
                    break
                else:
                    judge_scores[name] = judge_result.get("score")
        case_results.append(
            BenchmarkCaseResult(
                scenario=task.scenario,
                task_id=task.task_id,
                profile=profile_name,
                agent_status=str(runtime_result.get("status", "UNKNOWN")),
                llm_provider=str(runtime_meta.get("llm_provider", "")),
                llm_model=str(runtime_meta.get("llm_model", "")),
                judge_model=runtime_meta.get("judge_model"),
                failure_bucket=failure_bucket,
                scenario_score=scenario_score,
                scenario_metrics=scenario_metrics,
                judge_scores=judge_scores,
                timing=dict(runtime_result.get("timing", {})),
                artifact_refs=dict(runtime_result.get("artifact_refs", {})),
            )
        )

    summary = {
        "total_cases": len(case_results),
        "success_cases": sum(1 for case in case_results if case.failure_bucket == FailureBucket.SUCCESS),
    }
    benchmark_scenario = scenario or (case_results[0].scenario if case_results else "unknown")
    result = BenchmarkRunResult(
        run_id=run_id,
        profile=profile_name,
        scenario=benchmark_scenario,
        case_results=case_results,
        summary=summary,
    )
    # Ensure reporting helpers can consume the result shape immediately.
    run_result_to_json_dict(result)
    return result


def _run_with_profile_retries(runtime_target: RuntimeTarget, task: Any, rerun_count: int) -> dict[str, Any]:
    last_result: dict[str, Any] | None = None
    for _ in range(max(1, rerun_count)):
        try:
            last_result = runtime_target(task)
        except Exception as exc:
            last_result = {
                "status": "INFRA_FAILURE",
                "outputs": {},
                "runtime": {},
                "artifact_refs": {},
                "timing": {},
                "error": str(exc),
            }
    assert last_result is not None
    return last_result


def _classify_runtime_status(runtime_result: dict[str, Any]) -> FailureBucket:
    status = str(runtime_result.get("status", "")).upper()
    if status == "COMPLETED":
        return FailureBucket.SUCCESS
    if status == "RUNNING":
        return FailureBucket.GENERATION_FAILURE
    if status == "INFRA_FAILURE":
        return FailureBucket.INFRA_FAILURE
    if status in {"FAILED", "GENERATION_FAILURE"}:
        return FailureBucket.GENERATION_FAILURE
    return FailureBucket.INFRA_FAILURE
