from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from data_models import Event, EventType
from trace_store.service import TraceStore, TraceStoreConfig
from tracing.sinks import JsonlMirrorSink, LangSmithPrimarySink, RecorderSinkAdapter, TraceSinkFanout


class InMemoryPrimarySink:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def append_event(self, event: Event) -> None:
        self.events.append(event)


class FailingMirrorSink:
    def __init__(self) -> None:
        self.calls = 0

    def append_event(self, event: Event) -> None:
        _ = event
        self.calls += 1
        raise RuntimeError("mirror failure")


class FakeLangSmithClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_event(self, **kwargs) -> None:
        self.calls.append(kwargs)


class TraceSinksTests(unittest.TestCase):
    def test_jsonl_mirror_sink_persists_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TraceStore(TraceStoreConfig(storage_path=str(Path(tmpdir) / "events.jsonl")))
            sink = JsonlMirrorSink(store)
            event = Event(
                event_id="event-1",
                run_id="run-1",
                branch_id="main",
                loop_index=0,
                step_name="record",
                event_type=EventType.TRACE_RECORDED,
                payload={"status": "RECORDED"},
            )

            sink.append_event(event)

            events = store.query_events(run_id="run-1")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_id, "event-1")

    def test_fanout_keeps_primary_success_when_mirror_fails(self) -> None:
        primary = InMemoryPrimarySink()
        mirror = FailingMirrorSink()
        fanout = TraceSinkFanout(primary=primary, mirrors=(mirror,))
        event = Event(
            event_id="event-2",
            run_id="run-2",
            branch_id="main",
            loop_index=1,
            step_name="feedback",
            event_type=EventType.FEEDBACK_GENERATED,
            payload={"acceptable": True},
        )

        fanout.append_event(event)

        self.assertEqual(len(primary.events), 1)
        self.assertEqual(primary.events[0].event_id, "event-2")
        self.assertEqual(mirror.calls, 1)

    def test_langsmith_primary_sink_forwards_event_to_client(self) -> None:
        client = FakeLangSmithClient()
        sink = LangSmithPrimarySink(tracing_config=object(), client=client)
        event = Event(
            event_id="event-3",
            run_id="run-3",
            branch_id="branch-a",
            loop_index=3,
            step_name="running",
            event_type=EventType.EXECUTION_FINISHED,
            payload={"api_key": "secret", "status": "SUCCESS"},
        )

        sink.append_event(event)

        self.assertEqual(len(client.calls), 1)
        call = client.calls[0]
        self.assertEqual(call["name"], EventType.EXECUTION_FINISHED.value)
        self.assertEqual(call["run_id"], "run-3")
        metadata = call["metadata"]
        assert isinstance(metadata, dict)
        self.assertEqual(metadata["branch_id"], "branch-a")
        self.assertEqual(metadata["loop_index"], 3)
        self.assertEqual(metadata["step_name"], "running")
        self.assertEqual(metadata["api_key"], "***")
        self.assertEqual(metadata["event_id"], "event-3")
        self.assertIn("timestamp", metadata)

    def test_langsmith_primary_sink_warns_when_client_is_missing(self) -> None:
        sink = LangSmithPrimarySink(tracing_config=object(), client=None)
        event = Event(
            event_id="event-4",
            run_id="run-4",
            branch_id="main",
            loop_index=0,
            step_name="record",
            event_type=EventType.TRACE_RECORDED,
            payload={},
        )

        with self.assertLogs("tracing.sinks", level="WARNING") as captured:
            sink.append_event(event)

        self.assertIn("dropping event event-4", captured.output[0])

    def test_recorder_sink_adapter_converts_boundary_callback_to_event(self) -> None:
        primary = InMemoryPrimarySink()
        recorder = RecorderSinkAdapter(
            sink=primary,
            event_type=EventType.TRACE_RECORDED,
            branch_id="main",
        )

        recorder.record(
            run_id="run-3",
            scenario="data_science",
            loop_iteration=2,
            last_completed_node="feedback",
            next_node="record",
            checkpoint_id="loop-0002-feedback",
            payload={"feedback_id": "fb-1"},
        )

        self.assertEqual(len(primary.events), 1)
        event = primary.events[0]
        self.assertEqual(event.run_id, "run-3")
        self.assertEqual(event.branch_id, "main")
        self.assertEqual(event.loop_index, 2)
        self.assertEqual(event.step_name, "feedback")
        self.assertEqual(event.event_type, EventType.TRACE_RECORDED)
        self.assertEqual(event.payload["scenario"], "data_science")
        self.assertEqual(event.payload["next_node"], "record")
        self.assertEqual(event.payload["checkpoint_id"], "loop-0002-feedback")

    def test_recorder_sink_adapter_allows_branch_override_from_payload(self) -> None:
        primary = InMemoryPrimarySink()
        recorder = RecorderSinkAdapter(sink=primary, branch_id="main")

        recorder.record(
            run_id="run-5",
            scenario="quant",
            loop_iteration=1,
            last_completed_node="coding",
            checkpoint_id="loop-0001-coding",
            payload={"branch_id": "fork-1", "artifact_id": "artifact-1"},
        )

        self.assertEqual(len(primary.events), 1)
        event = primary.events[0]
        self.assertEqual(event.branch_id, "fork-1")
        self.assertEqual(event.payload["artifact_id"], "artifact-1")


if __name__ == "__main__":
    unittest.main()
