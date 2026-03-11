from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tests.golden_tasks.benchmark import create_benchmark_llm_adapter, load_golden_tasks, run_single_round


def main() -> None:
    adapter, model_config = create_benchmark_llm_adapter()
    scenario_names = ("quant", "data_science", "synthetic_research")
    results: dict[str, dict[str, object]] = {}

    for scenario in scenario_names:
        tasks = load_golden_tasks(scenario)
        task_results = [run_single_round(task, adapter, model_config) for task in tasks]
        passed = sum(1 for result in task_results if result.passed)
        results[scenario] = {
            "total": len(task_results),
            "passed": passed,
            "failed_task_ids": [result.task_id for result in task_results if not result.passed],
        }

    aggregate_total = sum(int(result["total"]) for result in results.values())
    aggregate_passed = sum(int(result["passed"]) for result in results.values())
    baseline = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model_config.model,
        "temperature": model_config.temperature,
        "results": results,
        "aggregate_pass_rate": (aggregate_passed / aggregate_total) if aggregate_total else 0.0,
    }

    output_path = Path(__file__).parent / "baseline.json"
    output_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    print(json.dumps(baseline, indent=2))


if __name__ == "__main__":
    main()
