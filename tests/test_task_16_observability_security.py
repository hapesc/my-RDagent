"""Task-16 tests for observability baseline and trace redaction."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.storage import SQLiteMetadataStore, SQLiteStoreConfig
from data_models import Event, EventType
from observability import Observability, ObservabilityConfig, sanitize_payload


class SecurityRedactionTests(unittest.TestCase):
    def test_sanitize_payload_redacts_sensitive_fields(self) -> None:
        payload = {
            "api_key": "secret-key",
            "nested": {
                "token": "abc",
                "safe": "ok",
            },
            "items": [{"password": "p1"}, {"value": 1}],
        }
        sanitized = sanitize_payload(payload)
        self.assertEqual(sanitized["api_key"], "***")
        self.assertEqual(sanitized["nested"]["token"], "***")
        self.assertEqual(sanitized["nested"]["safe"], "ok")
        self.assertEqual(sanitized["items"][0]["password"], "***")

    def test_sqlite_trace_redacts_sensitive_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sqlite_path = str(Path(tmpdir) / "meta.db")
            store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path))
            store.append_event(
                Event(
                    event_id="event-sec-1",
                    run_id="run-sec-1",
                    branch_id="main",
                    loop_index=0,
                    step_name="trace",
                    event_type=EventType.TRACE_RECORDED,
                    payload={"authorization": "Bearer 123", "safe": "ok"},
                )
            )
            events = store.query_events(run_id="run-sec-1")
            self.assertEqual(events[0].payload["authorization"], "***")
            self.assertEqual(events[0].payload["safe"], "ok")


class ObservabilityTests(unittest.TestCase):
    def test_structured_log_metric_trace_and_context(self) -> None:
        obs = Observability(ObservabilityConfig(log_level="INFO"))
        obs.emit_log("step_failed", {"run_id": "run-16", "step": "coding", "api_key": "k"})
        obs.emit_metric("loops_completed", 1.0, {"run_id": "run-16", "step": "record"})
        obs.emit_trace("trace-1", "execution", {"run_id": "run-16", "token": "x"})

        records = obs.query_observability({"run_id": "run-16"})
        self.assertEqual(len(records), 3)
        log_record = next(record for record in records if record["kind"] == "log")
        self.assertEqual(log_record["context"]["api_key"], "***")
        self.assertEqual(log_record["context"]["run_id"], "run-16")

        metrics = obs.snapshot_metrics()
        self.assertEqual(metrics["loops_completed"], 1.0)


if __name__ == "__main__":
    unittest.main()
