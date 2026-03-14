from __future__ import annotations

import unittest

from benchmarking.langsmith_backend import (
    HostedLangSmithExperimentClient,
    LangSmithBackend,
    NullLangSmithExperimentClient,
)
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

    def test_null_client_produces_stable_local_publish_handles(self) -> None:
        backend = LangSmithBackend(client=NullLangSmithExperimentClient())
        run_result = BenchmarkRunResult(
            run_id="run-backend-local",
            profile="smoke",
            scenario="data_science",
            case_results=[],
            summary={"total_cases": 0},
        )

        result = backend.publish_run(
            run_result,
            dataset_name="rdagent-smoke",
            experiment_name="smoke-local",
            case_evaluators=("rules",),
            summary_evaluators=("aggregate_pass_rate",),
        )

        self.assertEqual(result["dataset"]["dataset_id"], "local-rdagent-smoke")
        self.assertEqual(result["experiment"]["experiment_id"], "local-smoke-local")

    def test_hosted_client_adapter_normalizes_sdk_objects(self) -> None:
        class Dataset:
            id = "dataset-hosted"
            name = "rdagent-hosted"
            description = "hosted dataset"

        class Project:
            id = "project-hosted"
            name = "smoke-hosted"

        class FakeSdkClient:
            def read_dataset(self, *, dataset_name: str):
                _ = dataset_name
                raise RuntimeError("not found")

            def create_dataset(self, dataset_name: str, *, description: str):
                _ = (dataset_name, description)
                return Dataset()

            def create_project(self, project_name: str, *, metadata: dict, upsert: bool, reference_dataset_id: str):
                _ = (project_name, metadata, upsert, reference_dataset_id)
                return Project()

        client = HostedLangSmithExperimentClient(FakeSdkClient())
        dataset = client.ensure_dataset(dataset_name="rdagent-hosted", description="hosted dataset")
        experiment = client.create_experiment(
            dataset_id="dataset-hosted",
            experiment_name="smoke-hosted",
            metadata={"profile": "smoke"},
        )

        self.assertEqual(dataset["dataset_id"], "dataset-hosted")
        self.assertEqual(dataset["dataset_name"], "rdagent-hosted")
        self.assertEqual(experiment["experiment_id"], "project-hosted")
        self.assertEqual(experiment["experiment_name"], "smoke-hosted")


if __name__ == "__main__":
    unittest.main()
