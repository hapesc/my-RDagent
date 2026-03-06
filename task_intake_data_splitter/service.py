"""Service scaffold for Task Intake & Data Splitter."""

from __future__ import annotations

import csv
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from data_models import DataSplitManifest, DataSummaryReport, TaskArtifacts, TaskSpec

logger = logging.getLogger(__name__)


@dataclass
class TaskIntakeConfig:
    """Configuration for task intake behavior."""

    default_train_ratio: float = 0.7
    default_val_ratio: float = 0.2
    default_test_ratio: float = 0.1
    default_seed: int = 0


@dataclass
class _SplitConfig:
    train_ratio: float
    val_ratio: float
    test_ratio: float
    seed: int
    strategy: str
    id_column: Optional[str]
    time_column: Optional[str]
    group_column: Optional[str]
    stratify_by: Optional[str]


class TaskIntakeDataSplitter:
    """Parses task input and prepares fixed dataset splits and summaries."""

    def __init__(self, config: TaskIntakeConfig) -> None:
        """Initialize with split defaults and deterministic seed settings."""

        self._config = config
        self._artifacts: Dict[str, TaskArtifacts] = {}

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

        logger.info("task_intake.start task_id=%s data_source=%s", task_id, data_source)
        task_spec = TaskSpec(task_id=task_id, description=description, constraints=constraints)
        split_config = self._parse_constraints(constraints)

        rows = self._load_rows(data_source)
        if not rows:
            logger.warning("task_intake.empty_dataset task_id=%s", task_id)
            summary_report = DataSummaryReport(row_count=0, field_types={}, missing_rates={})
            split_manifest = DataSplitManifest(
                train_ids=[],
                val_ids=[],
                test_ids=[],
                seed=split_config.seed,
            )
            artifacts = TaskArtifacts(
                task_spec=task_spec,
                split_manifest=split_manifest,
                summary_report=summary_report,
            )
            self._artifacts[task_id] = artifacts
            return artifacts

        summary_report = self._build_summary(rows)
        split_manifest = self._split_rows(rows, split_config)
        artifacts = TaskArtifacts(
            task_spec=task_spec,
            split_manifest=split_manifest,
            summary_report=summary_report,
        )
        self._artifacts[task_id] = artifacts
        logger.info(
            "task_intake.done task_id=%s rows=%d train=%d val=%d test=%d",
            task_id,
            summary_report.row_count,
            len(split_manifest.train_ids),
            len(split_manifest.val_ids),
            len(split_manifest.test_ids),
        )
        return artifacts

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

        if task_id in self._artifacts:
            logger.info("task_intake.fetch task_id=%s hit=true", task_id)
            return self._artifacts[task_id]
        logger.warning("task_intake.fetch task_id=%s hit=false", task_id)
        task_spec = TaskSpec(task_id=task_id, description="placeholder", constraints={})
        split_manifest = DataSplitManifest(seed=self._config.default_seed)
        summary_report = DataSummaryReport(row_count=0, field_types={}, missing_rates={})
        return TaskArtifacts(
            task_spec=task_spec,
            split_manifest=split_manifest,
            summary_report=summary_report,
        )

    def _parse_constraints(self, constraints: Dict[str, str]) -> _SplitConfig:
        train_ratio = self._parse_float(constraints.get("train_ratio"), self._config.default_train_ratio)
        val_ratio = self._parse_float(constraints.get("val_ratio"), self._config.default_val_ratio)
        test_ratio = self._parse_float(constraints.get("test_ratio"), self._config.default_test_ratio)
        seed = int(self._parse_float(constraints.get("seed"), float(self._config.default_seed)))
        total = train_ratio + val_ratio + test_ratio
        if total <= 0:
            raise ValueError("split ratios sum to zero")
        if abs(total - 1.0) > 1e-6:
            logger.warning("task_intake.normalize_ratios total=%.4f", total)
            train_ratio, val_ratio, test_ratio = (
                train_ratio / total,
                val_ratio / total,
                test_ratio / total,
            )

        id_column = constraints.get("id_column")
        time_column = constraints.get("time_column")
        group_column = constraints.get("group_column")
        stratify_by = constraints.get("stratify_by")
        strategy = constraints.get("split_strategy", "").lower()
        if not strategy:
            if time_column:
                strategy = "time"
            elif group_column:
                strategy = "group"
            elif stratify_by:
                strategy = "stratified"
            else:
                strategy = "random"

        logger.info(
            "task_intake.constraints strategy=%s ratios=%.2f/%.2f/%.2f seed=%d",
            strategy,
            train_ratio,
            val_ratio,
            test_ratio,
            seed,
        )
        return _SplitConfig(
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed,
            strategy=strategy,
            id_column=id_column,
            time_column=time_column,
            group_column=group_column,
            stratify_by=stratify_by,
        )

    def _parse_float(self, value: Optional[str], default: float) -> float:
        if value is None or value == "":
            return default
        return float(value)

    def _load_rows(self, data_source: str) -> List[Dict[str, str]]:
        if not data_source or data_source == "data-source-placeholder":
            logger.warning("task_intake.data_source_missing")
            return []

        path = Path(data_source)
        if not path.exists():
            logger.warning("task_intake.data_source_not_found path=%s", data_source)
            return []

        if path.suffix.lower() == ".csv":
            return self._load_csv(path)
        if path.suffix.lower() in {".jsonl", ".ndjson"}:
            return self._load_jsonl(path)

        raise ValueError(f"unsupported data_source format: {path.suffix}")

    def _load_csv(self, path: Path) -> List[Dict[str, str]]:
        logger.info("task_intake.load_csv path=%s", path)
        rows: List[Dict[str, str]] = []
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(dict(row))
        logger.info("task_intake.load_csv_done rows=%d", len(rows))
        return rows

    def _load_jsonl(self, path: Path) -> List[Dict[str, str]]:
        logger.info("task_intake.load_jsonl path=%s", path)
        rows: List[Dict[str, str]] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        logger.info("task_intake.load_jsonl_done rows=%d", len(rows))
        return rows

    def _build_summary(self, rows: List[Dict[str, str]]) -> DataSummaryReport:
        row_count = len(rows)
        if row_count == 0:
            return DataSummaryReport(row_count=0, field_types={}, missing_rates={})

        field_types: Dict[str, Dict[str, int]] = {}
        missing_counts: Dict[str, int] = {}
        for row in rows:
            for field, value in row.items():
                if field not in field_types:
                    field_types[field] = {}
                    missing_counts[field] = 0
                inferred = self._infer_type(value)
                if inferred == "missing":
                    missing_counts[field] += 1
                    continue
                field_types[field][inferred] = field_types[field].get(inferred, 0) + 1

        final_types = {field: self._pick_type(counts) for field, counts in field_types.items()}
        missing_rates = {
            field: (missing_counts.get(field, 0) / row_count) for field in final_types.keys()
        }
        logger.info("task_intake.summary rows=%d fields=%d", row_count, len(final_types))
        return DataSummaryReport(
            row_count=row_count,
            field_types=final_types,
            missing_rates=missing_rates,
        )

    def _infer_type(self, value: Optional[str]) -> str:
        if value is None:
            return "missing"
        if isinstance(value, str):
            if value.strip() == "":
                return "missing"
            lowered = value.strip().lower()
            if lowered in {"true", "false"}:
                return "bool"
            if self._is_int(lowered):
                return "int"
            if self._is_float(lowered):
                return "float"
            if self._is_datetime(lowered):
                return "datetime"
            return "str"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        return "str"

    def _is_int(self, value: str) -> bool:
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _is_float(self, value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _is_datetime(self, value: str) -> bool:
        try:
            datetime.fromisoformat(value)
            return True
        except ValueError:
            return False

    def _pick_type(self, counts: Dict[str, int]) -> str:
        if not counts:
            return "unknown"
        return max(counts.items(), key=lambda item: item[1])[0]

    def _split_rows(self, rows: List[Dict[str, str]], config: _SplitConfig) -> DataSplitManifest:
        row_ids = self._extract_row_ids(rows, config.id_column)
        indexed_rows = list(zip(row_ids, rows))
        rng = random.Random(config.seed)
        train_count, val_count, test_count = self._allocate_counts(
            len(indexed_rows),
            config.train_ratio,
            config.val_ratio,
            config.test_ratio,
        )

        strategy = config.strategy
        if strategy == "time":
            split_ids = self._split_by_time(indexed_rows, config.time_column, train_count, val_count)
        elif strategy == "group":
            split_ids = self._split_by_group(indexed_rows, config.group_column, train_count, val_count, rng)
        elif strategy == "stratified":
            split_ids = self._split_by_stratified(
                indexed_rows,
                config.stratify_by,
                train_count,
                val_count,
                rng,
            )
        else:
            split_ids = self._split_by_random(indexed_rows, train_count, val_count, rng)

        train_ids, val_ids, test_ids = split_ids
        logger.info("task_intake.split strategy=%s total=%d", strategy, len(indexed_rows))
        return DataSplitManifest(
            train_ids=train_ids,
            val_ids=val_ids,
            test_ids=test_ids,
            seed=config.seed,
        )

    def _extract_row_ids(self, rows: List[Dict[str, str]], id_column: Optional[str]) -> List[str]:
        row_ids: List[str] = []
        seen: Dict[str, int] = {}
        for idx, row in enumerate(rows):
            raw_id = None
            if id_column and id_column in row and row[id_column] not in {None, ""}:
                raw_id = str(row[id_column])
            if raw_id is None:
                raw_id = f"row-{idx}"
            if raw_id in seen:
                seen[raw_id] += 1
                raw_id = f"{raw_id}-{seen[raw_id]}"
            else:
                seen[raw_id] = 0
            row_ids.append(raw_id)
        return row_ids

    def _allocate_counts(
        self,
        total: int,
        train_ratio: float,
        val_ratio: float,
        test_ratio: float,
    ) -> Tuple[int, int, int]:
        train_count = int(total * train_ratio)
        val_count = int(total * val_ratio)
        test_count = total - train_count - val_count
        if test_count < 0:
            test_count = 0
            train_count = max(0, total - val_count)
        return train_count, val_count, test_count

    def _split_by_random(
        self,
        rows: List[Tuple[str, Dict[str, str]]],
        train_count: int,
        val_count: int,
        rng: random.Random,
    ) -> Tuple[List[str], List[str], List[str]]:
        rng.shuffle(rows)
        train = [row_id for row_id, _ in rows[:train_count]]
        val = [row_id for row_id, _ in rows[train_count : train_count + val_count]]
        test = [row_id for row_id, _ in rows[train_count + val_count :]]
        return train, val, test

    def _split_by_time(
        self,
        rows: List[Tuple[str, Dict[str, str]]],
        time_column: Optional[str],
        train_count: int,
        val_count: int,
    ) -> Tuple[List[str], List[str], List[str]]:
        if not time_column:
            raise ValueError("time_column required for time-based split")
        sorted_rows = sorted(rows, key=lambda item: self._time_key(item[1].get(time_column)))
        train = [row_id for row_id, _ in sorted_rows[:train_count]]
        val = [row_id for row_id, _ in sorted_rows[train_count : train_count + val_count]]
        test = [row_id for row_id, _ in sorted_rows[train_count + val_count :]]
        return train, val, test

    def _time_key(self, value: Optional[str]) -> Tuple[int, str]:
        if value is None or str(value).strip() == "":
            return (1, "")
        text = str(value)
        try:
            parsed = datetime.fromisoformat(text)
            return (0, parsed.isoformat())
        except ValueError:
            return (0, text)

    def _split_by_group(
        self,
        rows: List[Tuple[str, Dict[str, str]]],
        group_column: Optional[str],
        train_count: int,
        val_count: int,
        rng: random.Random,
    ) -> Tuple[List[str], List[str], List[str]]:
        if not group_column:
            raise ValueError("group_column required for group-based split")
        groups: Dict[str, List[str]] = {}
        for row_id, row in rows:
            key = str(row.get(group_column, "missing"))
            groups.setdefault(key, []).append(row_id)

        group_items = list(groups.items())
        rng.shuffle(group_items)
        split_targets = {
            "train": train_count,
            "val": val_count,
            "test": len(rows) - train_count - val_count,
        }
        split_ids = {"train": [], "val": [], "test": []}
        for group_key, ids in group_items:
            remaining = {k: split_targets[k] - len(split_ids[k]) for k in split_ids}
            chosen = max(remaining.items(), key=lambda item: item[1])[0]
            split_ids[chosen].extend(ids)
            logger.debug("task_intake.group_assign group=%s split=%s size=%d", group_key, chosen, len(ids))

        return split_ids["train"], split_ids["val"], split_ids["test"]

    def _split_by_stratified(
        self,
        rows: List[Tuple[str, Dict[str, str]]],
        stratify_by: Optional[str],
        train_count: int,
        val_count: int,
        rng: random.Random,
    ) -> Tuple[List[str], List[str], List[str]]:
        if not stratify_by:
            raise ValueError("stratify_by required for stratified split")
        buckets: Dict[str, List[str]] = {}
        for row_id, row in rows:
            key = str(row.get(stratify_by, "missing"))
            buckets.setdefault(key, []).append(row_id)

        train_ids: List[str] = []
        val_ids: List[str] = []
        test_ids: List[str] = []
        for key, ids in buckets.items():
            rng.shuffle(ids)
            train_local, val_local, _ = self._allocate_counts(
                len(ids),
                train_count / len(rows) if rows else 0.0,
                val_count / len(rows) if rows else 0.0,
                0.0,
            )
            train_ids.extend(ids[:train_local])
            val_ids.extend(ids[train_local : train_local + val_local])
            test_ids.extend(ids[train_local + val_local :])
            logger.debug("task_intake.stratify bucket=%s size=%d", key, len(ids))

        return train_ids, val_ids, test_ids
