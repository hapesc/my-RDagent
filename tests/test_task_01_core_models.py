"""Task-01 contract tests for core model freeze."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from data_models import (
    Event,
    EventType,
    ExperimentNode,
    FeedbackRecord,
    FileManifestEntry,
    RunSession,
    RunStatus,
    StepState,
    StopConditions,
    WorkspaceSnapshot,
)

class CoreModelContractTests(unittest.TestCase):
    def test_run_session_and_event_serialization(self) -> None:
        session = RunSession(
            run_id="run-test-001",
            scenario="data_science",
            status=RunStatus.RUNNING,
            stop_conditions=StopConditions(max_loops=5, max_steps=50, max_duration_sec=600),
            entry_input={"task_id": "task-001"},
            active_branch_ids=["main"],
        )
        payload = session.to_dict()

        self.assertEqual(payload["status"], "RUNNING")
        self.assertEqual(payload["stop_conditions"]["max_loops"], 5)
        self.assertTrue(payload["created_at"].endswith("Z"))

        event = Event(
            event_id="event-1",
            run_id="run-test-001",
            branch_id="main",
            loop_index=0,
            step_name="run",
            event_type=EventType.RUN_CREATED,
            payload={"scenario": "data_science"},
        )
        event_payload = event.to_dict()

        self.assertEqual(event_payload["event_type"], "run.created")
        self.assertEqual(event_payload["payload"]["scenario"], "data_science")

    def test_experiment_workspace_feedback_models(self) -> None:
        node = ExperimentNode(
            node_id="node-1",
            run_id="run-test-001",
            branch_id="main",
            parent_node_id=None,
            loop_index=1,
            step_state=StepState.RECORDED,
            hypothesis={"text": "baseline", "component": "model"},
            workspace_ref="artifacts/run-test-001/node-1/workspace",
            result_ref="artifacts/run-test-001/node-1/result",
            feedback_ref="trace:event-2",
        )
        snapshot = WorkspaceSnapshot(
            workspace_id="ws-1",
            run_id="run-test-001",
            file_manifest=[FileManifestEntry(path="main.py", sha256="abc")],
            checkpoint_type="zip",
        )
        feedback = FeedbackRecord(
            feedback_id="fb-1",
            decision=True,
            acceptable=True,
            reason="metric improved",
            observations="stable runtime",
            code_change_summary="added feature",
        )

        self.assertEqual(node.to_dict()["step_state"], "RECORDED")
        self.assertEqual(snapshot.to_dict()["file_manifest"][0]["path"], "main.py")
        self.assertTrue(feedback.to_dict()["decision"])

    def test_schema_example_is_present(self) -> None:
        schema_path = Path("dev_doc/schema_examples/task_01_core_models.json")
        self.assertTrue(schema_path.exists())

        content = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertIn("run_session", content)
        self.assertIn("experiment_node", content)
        self.assertIn("workspace_snapshot", content)
        self.assertIn("feedback_record", content)
        self.assertIn("event", content)


class ModelLayerUsageTests(unittest.TestCase):
    def test_core_services_import_model_layer(self) -> None:
        core_service_files = [
            "task_intake_data_splitter/service.py",
            "planner/service.py",
            "exploration_manager/service.py",
            "memory_service/service.py",
            "evaluation_service/service.py",
        ]

        for file_path in core_service_files:
            source = Path(file_path).read_text(encoding="utf-8")
            self.assertIn("from data_models import", source, msg=f"missing model-layer import: {file_path}")


if __name__ == "__main__":
    unittest.main()
