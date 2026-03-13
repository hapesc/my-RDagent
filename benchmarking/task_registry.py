"""Benchmark task registry for local fixtures and adapter-backed profiles."""

from __future__ import annotations

import json
import os
from pathlib import Path

from benchmarking.contracts import BenchmarkTask
from benchmarking.profiles import get_profile

_DEFAULT_FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "tests" / "golden_tasks"


def materialize_tasks(
    profile_name: str,
    scenario: str | None = None,
    fixture_root: Path | None = None,
) -> list[BenchmarkTask]:
    profile = get_profile(profile_name)
    scenarios = (scenario,) if scenario is not None else profile.scenarios
    resolved_fixture_root = fixture_root or Path(
        os.environ.get("RD_AGENT_BENCHMARK_FIXTURE_ROOT", str(_DEFAULT_FIXTURE_ROOT))
    )

    tasks: list[BenchmarkTask] = []
    if profile_name == "smoke":
        for scenario_name in scenarios:
            tasks.extend(_local_fixture_tasks(scenario_name, resolved_fixture_root, limit=1))
        return tasks

    for scenario_name in scenarios:
        tasks.extend(_local_fixture_tasks(scenario_name, resolved_fixture_root))
        if scenario_name == "data_science":
            tasks.append(_adapter_task(scenario_name, "mlebench"))
        elif scenario_name == "quant":
            tasks.append(_adapter_task(scenario_name, "quanteval"))
    return tasks


def _local_fixture_tasks(scenario: str, fixture_root: Path, limit: int | None = None) -> list[BenchmarkTask]:
    tasks: list[BenchmarkTask] = []
    for path in sorted(fixture_root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("scenario") != scenario:
            continue
        tasks.append(
            BenchmarkTask(
                scenario=scenario,
                task_id=str(payload["task_id"]),
                task_summary=str(payload["task_summary"]),
                source_type="local_fixture",
                inputs={
                    "task_summary": payload["task_summary"],
                    "artifact_type": payload.get("artifact_type"),
                    "difficulty": payload.get("difficulty"),
                },
                reference_outputs={
                    "fixture_path": str(path),
                    "expected_properties": dict(payload.get("expected_properties", {})),
                },
                tags=(str(payload.get("difficulty", "unknown")), "golden-task"),
            )
        )
        if limit is not None and len(tasks) >= limit:
            break
    return tasks


def _adapter_task(scenario: str, source_type: str) -> BenchmarkTask:
    task_id = f"{scenario}-{source_type}-seed"
    return BenchmarkTask(
        scenario=scenario,
        task_id=task_id,
        task_summary=f"{scenario} adapter-backed benchmark seed",
        source_type=source_type,
        inputs={"task_summary": f"{scenario} benchmark seed"},
        reference_outputs={"adapter": source_type},
        tags=("adapter-seed", scenario),
    )
