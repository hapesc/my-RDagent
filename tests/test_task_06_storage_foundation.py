"""Task-06 tests for persistence foundation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.storage import (
    CheckpointStoreConfig,
    FileCheckpointStore,
    SQLiteMetadataStore,
    SQLiteStoreConfig,
)
from data_models import Event, EventType, RunSession, RunStatus, StopConditions


class SQLiteMetadataStoreTests(unittest.TestCase):
    def test_run_create_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sqlite_path = Path(tmpdir) / "meta.db"
            store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=str(sqlite_path)))

            run = RunSession(
                run_id="run-1",
                scenario="data_science",
                status=RunStatus.RUNNING,
                stop_conditions=StopConditions(max_loops=2, max_duration_sec=60),
                entry_input={"task_id": "task-1"},
            )
            store.create_run(run)

            loaded = store.get_run("run-1")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.run_id, "run-1")
            self.assertEqual(loaded.status, RunStatus.RUNNING)
            self.assertEqual(len(store.list_runs()), 1)

    def test_event_append_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sqlite_path = Path(tmpdir) / "meta.db"
            store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=str(sqlite_path)))

            event = Event(
                event_id="event-1",
                run_id="run-1",
                branch_id="main",
                loop_index=0,
                step_name="run",
                event_type=EventType.RUN_CREATED,
                payload={"scenario": "data_science"},
            )
            store.append_event(event)

            events = store.query_events(run_id="run-1")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_type, EventType.RUN_CREATED)


class FileCheckpointStoreTests(unittest.TestCase):
    def test_checkpoint_crud(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_store = FileCheckpointStore(CheckpointStoreConfig(root_dir=tmpdir))
            run_id = "run-1"
            checkpoint_id = "step-1"
            payload = b"checkpoint-bytes"

            saved_path = checkpoint_store.save_checkpoint(run_id, checkpoint_id, payload)
            self.assertTrue(Path(saved_path).exists())

            loaded = checkpoint_store.load_checkpoint(run_id, checkpoint_id)
            self.assertEqual(loaded, payload)

            checkpoint_ids = checkpoint_store.list_checkpoints(run_id)
            self.assertEqual(checkpoint_ids, [checkpoint_id])

            deleted = checkpoint_store.delete_checkpoint(run_id, checkpoint_id)
            self.assertTrue(deleted)
            self.assertEqual(checkpoint_store.list_checkpoints(run_id), [])


if __name__ == "__main__":
    unittest.main()
