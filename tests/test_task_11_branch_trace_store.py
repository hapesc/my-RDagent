"""Task-11 tests for branch heads and branch-aware trace queries."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.storage import BranchTraceStore, BranchTraceStoreConfig, SQLiteMetadataStore, SQLiteStoreConfig
from data_models import Event, EventType, ExperimentNode, StepState


class BranchTraceStoreTests(unittest.TestCase):
    def test_main_and_fork_branch_can_coexist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sqlite_path = str(Path(tmpdir) / "meta.db")
            branch_store = BranchTraceStore(BranchTraceStoreConfig(sqlite_path=sqlite_path))

            root = ExperimentNode(
                node_id="node-0",
                run_id="run-11",
                branch_id="main",
                parent_node_id=None,
                loop_index=0,
                step_state=StepState.RECORDED,
                hypothesis={"text": "root"},
            )
            branch_store.record_node(root)

            main_child = branch_store.create_child_node(
                run_id="run-11",
                parent_node_id="node-0",
                node_id="node-1-main",
                loop_index=1,
                fork_branch=False,
                hypothesis={"text": "main child"},
            )
            fork_child = branch_store.create_child_node(
                run_id="run-11",
                parent_node_id="node-0",
                node_id="node-1-fork",
                loop_index=1,
                fork_branch=True,
                hypothesis={"text": "fork child"},
            )

            heads = branch_store.get_branch_heads("run-11")
            self.assertEqual(heads["main"], main_child.node_id)
            self.assertEqual(heads[fork_child.branch_id], fork_child.node_id)

            all_nodes = branch_store.query_nodes("run-11")
            self.assertEqual(len(all_nodes), 3)
            fork_nodes = branch_store.query_nodes("run-11", branch_id=fork_child.branch_id)
            self.assertEqual(len(fork_nodes), 1)
            self.assertEqual(fork_nodes[0].node_id, fork_child.node_id)

    def test_trace_query_supports_branch_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sqlite_path = str(Path(tmpdir) / "meta.db")
            event_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path))

            event_store.append_event(
                Event(
                    event_id="event-main",
                    run_id="run-11",
                    branch_id="main",
                    loop_index=0,
                    step_name="record",
                    event_type=EventType.TRACE_RECORDED,
                    payload={"branch": "main"},
                )
            )
            event_store.append_event(
                Event(
                    event_id="event-fork",
                    run_id="run-11",
                    branch_id="fork-1",
                    loop_index=1,
                    step_name="record",
                    event_type=EventType.TRACE_RECORDED,
                    payload={"branch": "fork"},
                )
            )

            main_events = event_store.query_events(run_id="run-11", branch_id="main")
            fork_events = event_store.query_events(run_id="run-11", branch_id="fork-1")

            self.assertEqual(len(main_events), 1)
            self.assertEqual(main_events[0].event_id, "event-main")
            self.assertEqual(len(fork_events), 1)
            self.assertEqual(fork_events[0].event_id, "event-fork")


if __name__ == "__main__":
    unittest.main()
