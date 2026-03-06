"""Task-17 reproducibility acceptance test."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from data_models import ContextPack, Plan, RunSession, RunStatus, StopConditions
from scenarios.data_science import DataScienceV1Config, build_data_science_v1_bundle
from task_intake_data_splitter import TaskIntakeConfig, TaskIntakeDataSplitter


class ReproducibilityAcceptanceTests(unittest.TestCase):
    def _write_csv(self, path: Path) -> None:
        rows = [
            {"id": "1", "x": "10", "label": "A"},
            {"id": "2", "x": "11", "label": "B"},
            {"id": "3", "x": "12", "label": "A"},
            {"id": "4", "x": "13", "label": "B"},
            {"id": "5", "x": "14", "label": "A"},
            {"id": "6", "x": "15", "label": "B"},
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def test_split_and_proposal_are_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "train.csv"
            self._write_csv(csv_path)

            splitter = TaskIntakeDataSplitter(TaskIntakeConfig())
            constraints = {
                "train_ratio": "0.5",
                "val_ratio": "0.25",
                "test_ratio": "0.25",
                "seed": "42",
                "id_column": "id",
            }
            a = splitter.prepare_task_artifacts("task-a", "repro", str(csv_path), constraints)
            b = splitter.prepare_task_artifacts("task-b", "repro", str(csv_path), constraints)

            self.assertEqual(a.split_manifest.train_ids, b.split_manifest.train_ids)
            self.assertEqual(a.split_manifest.val_ids, b.split_manifest.val_ids)
            self.assertEqual(a.split_manifest.test_ids, b.split_manifest.test_ids)

            bundle = build_data_science_v1_bundle(
                DataScienceV1Config(
                    workspace_root=str(Path(tmpdir) / "workspace"),
                    trace_storage_path=str(Path(tmpdir) / "trace.jsonl"),
                    prefer_docker=False,
                )
            )
            run_session = RunSession(
                run_id="run-repro",
                scenario="data_science",
                status=RunStatus.RUNNING,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
                entry_input={"task_id": "repro"},
            )
            scenario = bundle.scenario_plugin.build_context(run_session, {"task_summary": "same input"})
            plan = Plan(plan_id="plan-repro")
            proposal1 = bundle.proposal_engine.propose("same input", ContextPack(), [], plan, scenario)
            proposal2 = bundle.proposal_engine.propose("same input", ContextPack(), [], plan, scenario)

            self.assertEqual(proposal1.summary, proposal2.summary)
            self.assertEqual(proposal1.constraints, proposal2.constraints)


if __name__ == "__main__":
    unittest.main()
