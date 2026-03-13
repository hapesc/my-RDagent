from __future__ import annotations

import unittest

from benchmarking.langsmith_backend import LangSmithBackend
from benchmarking.result_schema import BenchmarkCaseResult, BenchmarkRunResult, FailureBucket


class FakeLangSmithClient:
    def __init__(self) -> None:
        self.datasets: list[dict] = []
        self.experiments: list[dict] = []

    def ensure_dataset(self, *, dataset_name: str, description: str) -> dict:
        payload = {"dataset_name": dataset_name, "description": description, "dataset_id": "dataset-1"}
        self.datasets.append(payload)
        return payload

    def create_experiment(self, *, dataset_id: str, experiment_name: str, metadata: dict) -> dict:
        payload = {
            "dataset_id": dataset_id,
            "experiment_name": experiment_name,
            "metadata": metadata,
            "experiment_id": "experiment-1",
        }
        self.experiments.append(payload)
        return payload


class LangSmithBackendTests(unittest.TestCase):
    def test_backend_creates_dataset_and_experiment_handles(self) -> None:
        backend = LangSmithBackend(client=FakeLangSmithClient())
        run_result = BenchmarkRunResult(
            run_id="run-backend-1",
            profile="smoke",
            scenario="data_science",
            case_results=[
                BenchmarkCaseResult(
                    scenario="data_science",
                    task_id="task-1",
                    profile="smoke",
                    agent_status="COMPLETED",
                    llm_provider="litellm",
                    llm_model="gpt-4.1-mini",
                    judge_model="gpt-4.1-mini",
                    failure_bucket=FailureBucket.SUCCESS,
                )
            ],
            summary={"total_cases": 1},
        )

        result = backend.publish_run(
            run_result,
            dataset_name="rdagent-smoke",
            experiment_name="smoke-2026-03-13",
            case_evaluators=("rules", "judge"),
            summary_evaluators=("aggregate_pass_rate",),
        )

        self.assertEqual(result["dataset"]["dataset_id"], "dataset-1")
        self.assertEqual(result["dataset"]["dataset_name"], "rdagent-smoke")
        self.assertEqual(result["experiment"]["experiment_id"], "experiment-1")
        self.assertEqual(result["summary"]["total_cases"], 1)
        self.assertEqual(result["evaluator_handles"]["case_evaluators"], ["rules", "judge"])
        self.assertEqual(result["evaluator_handles"]["summary_evaluators"], ["aggregate_pass_rate"])
        self.assertEqual(result["experiment"]["metadata"]["case_evaluators"], ["rules", "judge"])
        self.assertEqual(result["run_id"], "run-backend-1")

    def test_backend_exposes_case_and_summary_evaluator_registration(self) -> None:
        backend = LangSmithBackend(client=FakeLangSmithClient())
        handles = backend.build_evaluator_handles(
            case_evaluators=("rules", "scenario", "judge"),
            summary_evaluators=("aggregate_pass_rate",),
        )

        self.assertEqual(handles["case_evaluators"], ["rules", "scenario", "judge"])
        self.assertEqual(handles["summary_evaluators"], ["aggregate_pass_rate"])

    def test_backend_propagates_client_failures(self) -> None:
        class FailingClient:
            def ensure_dataset(self, *, dataset_name: str, description: str) -> dict:
                _ = (dataset_name, description)
                raise RuntimeError("auth failure")

        backend = LangSmithBackend(client=FailingClient())
        run_result = BenchmarkRunResult(
            run_id="run-backend-fail",
            profile="smoke",
            scenario="data_science",
            case_results=[],
            summary={},
        )

        with self.assertRaisesRegex(RuntimeError, "auth failure"):
            backend.publish_run(
                run_result,
                dataset_name="rdagent-smoke",
                experiment_name="smoke-fail",
            )


if __name__ == "__main__":
    unittest.main()
