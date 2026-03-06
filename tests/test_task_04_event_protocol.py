"""Task-04 tests for canonical event protocol and projections."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from data_models import CANONICAL_TRACE_EVENT_TYPES, Event, EventType
from trace_store import TraceStore, TraceStoreConfig, TraceTimelineView


class EventProtocolTests(unittest.TestCase):
    def test_event_round_trip_serialization(self) -> None:
        event = Event(
            event_id="event-1",
            run_id="run-1",
            branch_id="main",
            loop_index=0,
            step_name="trace",
            event_type=EventType.TRACE_RECORDED,
            payload={"proposal_id": "p-1"},
        )
        encoded = event.to_dict()
        decoded = Event.from_dict(encoded)

        self.assertEqual(decoded.event_id, event.event_id)
        self.assertEqual(decoded.event_type, EventType.TRACE_RECORDED)
        self.assertEqual(decoded.payload["proposal_id"], "p-1")

    def test_canonical_event_range_is_frozen(self) -> None:
        self.assertEqual(CANONICAL_TRACE_EVENT_TYPES[0], EventType.RUN_CREATED)
        self.assertEqual(CANONICAL_TRACE_EVENT_TYPES[-1], EventType.TRACE_RECORDED)

    def test_trace_store_and_ui_use_same_event_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "events.jsonl"
            store = TraceStore(TraceStoreConfig(storage_path=str(path)))
            e1 = Event(
                event_id="event-1",
                run_id="run-1",
                branch_id="main",
                loop_index=0,
                step_name="run",
                event_type=EventType.RUN_CREATED,
                payload={"scenario": "data_science"},
            )
            e2 = Event(
                event_id="event-2",
                run_id="run-1",
                branch_id="main",
                loop_index=0,
                step_name="trace",
                event_type=EventType.TRACE_RECORDED,
                payload={"score_id": "score-1"},
            )
            store.append_event(e1)
            store.append_event(e2)

            events = store.query_events(run_id="run-1")
            self.assertEqual(len(events), 2)
            self.assertTrue(all(isinstance(event, Event) for event in events))

            rows = TraceTimelineView().build_rows(events)
            self.assertEqual(rows[0]["event_type"], "run.created")
            self.assertEqual(rows[1]["event_type"], "trace.recorded")


if __name__ == "__main__":
    unittest.main()
