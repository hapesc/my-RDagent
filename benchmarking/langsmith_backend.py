"""LangSmith dataset and experiment orchestration helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any, Protocol

from benchmarking.result_schema import BenchmarkRunResult

if TYPE_CHECKING:
    from langsmith import Client as LangSmithSdkClient


class LangSmithExperimentClient(Protocol):
    def ensure_dataset(self, *, dataset_name: str, description: str) -> dict[str, Any]:
        ...

    def create_experiment(self, *, dataset_id: str, experiment_name: str, metadata: dict[str, Any]) -> dict[str, Any]:
        ...


class NullLangSmithExperimentClient:
    """No-op client used when upload plumbing is enabled without a real client."""

    def ensure_dataset(self, *, dataset_name: str, description: str) -> dict[str, Any]:
        return {
            "dataset_id": f"local-{dataset_name}",
            "dataset_name": dataset_name,
            "description": description,
        }

    def create_experiment(self, *, dataset_id: str, experiment_name: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "experiment_id": f"local-{experiment_name}",
            "experiment_name": experiment_name,
            "dataset_id": dataset_id,
            "metadata": metadata,
        }


class HostedLangSmithExperimentClient:
    """Thin adapter around the hosted LangSmith SDK client."""

    def __init__(self, client: "LangSmithSdkClient") -> None:
        self._client = client

    def ensure_dataset(self, *, dataset_name: str, description: str) -> dict[str, Any]:
        try:
            dataset = self._client.read_dataset(dataset_name=dataset_name)
        except Exception:
            dataset = self._client.create_dataset(dataset_name, description=description)
        return {
            "dataset_id": str(getattr(dataset, "id")),
            "dataset_name": str(getattr(dataset, "name", dataset_name)),
            "description": getattr(dataset, "description", description),
        }

    def create_experiment(self, *, dataset_id: str, experiment_name: str, metadata: dict[str, Any]) -> dict[str, Any]:
        project = self._client.create_project(
            experiment_name,
            metadata=metadata,
            upsert=True,
            reference_dataset_id=dataset_id,
        )
        return {
            "experiment_id": str(getattr(project, "id")),
            "experiment_name": str(getattr(project, "name", experiment_name)),
            "dataset_id": dataset_id,
            "metadata": metadata,
        }


class LangSmithBackend:
    def __init__(self, client: LangSmithExperimentClient) -> None:
        self._client = client

    def publish_run(
        self,
        run_result: BenchmarkRunResult,
        *,
        dataset_name: str,
        experiment_name: str,
        case_evaluators: tuple[str, ...] | list[str] = (),
        summary_evaluators: tuple[str, ...] | list[str] = (),
    ) -> dict[str, Any]:
        evaluator_handles = self.build_evaluator_handles(
            case_evaluators=case_evaluators,
            summary_evaluators=summary_evaluators,
        )
        dataset = self._client.ensure_dataset(
            dataset_name=dataset_name,
            description=f"Benchmark dataset for {run_result.profile}/{run_result.scenario}",
        )
        experiment = self._client.create_experiment(
            dataset_id=dataset["dataset_id"],
            experiment_name=experiment_name,
            metadata={
                "run_id": run_result.run_id,
                "profile": run_result.profile,
                "scenario": run_result.scenario,
                "case_evaluators": evaluator_handles["case_evaluators"],
                "summary_evaluators": evaluator_handles["summary_evaluators"],
            },
        )
        return {
            "dataset": {
                "dataset_id": dataset["dataset_id"],
                "dataset_name": dataset["dataset_name"],
            },
            "experiment": {
                "experiment_id": experiment["experiment_id"],
                "experiment_name": experiment["experiment_name"],
                "dataset_id": experiment["dataset_id"],
                "metadata": experiment["metadata"],
            },
            "evaluator_handles": evaluator_handles,
            "run_id": run_result.run_id,
            "summary": dict(run_result.summary),
        }

    @staticmethod
    def build_evaluator_handles(
        *,
        case_evaluators: tuple[str, ...] | list[str],
        summary_evaluators: tuple[str, ...] | list[str],
    ) -> dict[str, list[str]]:
        return {
            "case_evaluators": list(case_evaluators),
            "summary_evaluators": list(summary_evaluators),
        }
