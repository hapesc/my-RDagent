"""Structured observability service with redaction and metric snapshots."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .redaction import sanitize_payload


@dataclass
class ObservabilityConfig:
    """Configuration for logging and monitoring."""

    log_level: str = "INFO"
    retention_days: int = 7


class Observability:
    """Collects structured logs, metrics, and traces for the system."""

    def __init__(self, config: ObservabilityConfig) -> None:
        self._config = config
        self._logs: list[dict[str, Any]] = []
        self._metrics: list[dict[str, Any]] = []
        self._traces: list[dict[str, Any]] = []
        self._metric_totals: dict[str, float] = {}
        self._logger = logging.getLogger("observability")
        self._logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    def emit_log(self, message: str, context: dict[str, str]) -> None:
        record = {
            "kind": "log",
            "timestamp": self._utc_now(),
            "message": message,
            "context": sanitize_payload(dict(context)),
        }
        self._logs.append(record)
        self._logger.info(json.dumps(record, ensure_ascii=False, sort_keys=True))

    def emit_metric(self, name: str, value: float, tags: dict[str, str]) -> None:
        record = {
            "kind": "metric",
            "timestamp": self._utc_now(),
            "name": name,
            "value": value,
            "tags": sanitize_payload(dict(tags)),
        }
        self._metrics.append(record)
        self._metric_totals[name] = self._metric_totals.get(name, 0.0) + float(value)
        self._logger.info(json.dumps(record, ensure_ascii=False, sort_keys=True))

    def emit_trace(self, trace_id: str, span_name: str, tags: dict[str, str]) -> None:
        record = {
            "kind": "trace",
            "timestamp": self._utc_now(),
            "trace_id": trace_id,
            "span_name": span_name,
            "tags": sanitize_payload(dict(tags)),
        }
        self._traces.append(record)
        self._logger.info(json.dumps(record, ensure_ascii=False, sort_keys=True))

    def query_observability(self, query: dict[str, str]) -> list[dict[str, str]]:
        needle_run_id = query.get("run_id")
        records: list[dict[str, Any]] = [*self._logs, *self._metrics, *self._traces]
        if needle_run_id:
            records = [
                record
                for record in records
                if record.get("context", {}).get("run_id") == needle_run_id
                or record.get("tags", {}).get("run_id") == needle_run_id
            ]
        return records

    def subscribe_alerts(self, filters: dict[str, str]) -> list[str]:
        alert_id = f"alert-{len(self._logs) + len(self._metrics) + len(self._traces)}"
        _ = filters
        return [alert_id]

    def snapshot_metrics(self) -> dict[str, float]:
        return dict(self._metric_totals)

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
