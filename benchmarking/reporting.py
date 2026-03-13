"""Reporting helpers for benchmark run summaries."""

from __future__ import annotations

from dataclasses import asdict

from benchmarking.result_schema import BenchmarkRunResult


def run_result_to_json_dict(result: BenchmarkRunResult) -> dict:
    return asdict(result)


def summarize_run_markdown(result: BenchmarkRunResult) -> str:
    total_cases = len(result.case_results)
    success_cases = sum(1 for case in result.case_results if case.failure_bucket.value == "success")
    return "\n".join(
        [
            f"# Benchmark Run {result.run_id}",
            "",
            f"- Profile: {result.profile}",
            f"- Scenario: {result.scenario}",
            f"- Total cases: {total_cases}",
            f"- Success cases: {success_cases}",
        ]
    )
