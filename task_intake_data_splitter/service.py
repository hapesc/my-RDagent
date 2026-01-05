"""Service scaffold for Task Intake & Data Splitter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from data_models import DataSplitManifest, DataSummaryReport, TaskArtifacts, TaskSpec


@dataclass
class TaskIntakeConfig:
    """Configuration for task intake behavior."""

    default_train_ratio: float = 0.7
    default_val_ratio: float = 0.2
    default_test_ratio: float = 0.1
    default_seed: int = 0


class TaskIntakeDataSplitter:
    """Parses task input and prepares fixed dataset splits and summaries."""

    def __init__(self, config: TaskIntakeConfig) -> None:
        """Initialize with split defaults and deterministic seed settings."""

        self._config = config

    def prepare_task_artifacts(
        self,
        task_id: str,
        description: str,
        data_source: str,
        constraints: Dict[str, str],
    ) -> TaskArtifacts:
        """Prepare task artifacts for the Task Intake & Data Splitter.

        Responsibility:
            Parse task input and generate fixed train/val/test split metadata
            along with a dataset summary report.
        Input semantics:
            - task_id: Unique identifier for the task
            - description: Human-readable task summary
            - data_source: Opaque data source pointer (not accessed here)
            - constraints: Split and data constraints
        Output semantics:
            TaskArtifacts containing TaskSpec, DataSplitManifest, and DataSummaryReport.
        Architecture mapping:
            Task Intake & Data Splitter -> prepare_task_artifacts
        """

        _ = data_source
        task_spec = TaskSpec(task_id=task_id, description=description, constraints=constraints)
        split_manifest = DataSplitManifest(
            train_ids=[],
            val_ids=[],
            test_ids=[],
            seed=self._config.default_seed,
        )
        summary_report = DataSummaryReport(row_count=0, field_types={}, missing_rates={})
        return TaskArtifacts(
            task_spec=task_spec,
            split_manifest=split_manifest,
            summary_report=summary_report,
        )

    def get_task_artifacts(self, task_id: str) -> TaskArtifacts:
        """Return task artifacts for a previously prepared task.

        Responsibility:
            Provide stored task artifacts by task ID.
        Input semantics:
            - task_id: Unique identifier for the task
        Output semantics:
            TaskArtifacts for the requested task.
        Architecture mapping:
            Task Intake & Data Splitter -> get_task_artifacts
        """

        task_spec = TaskSpec(task_id=task_id, description="placeholder", constraints={})
        split_manifest = DataSplitManifest(seed=self._config.default_seed)
        summary_report = DataSummaryReport(row_count=0, field_types={}, missing_rates={})
        return TaskArtifacts(
            task_spec=task_spec,
            split_manifest=split_manifest,
            summary_report=summary_report,
        )
