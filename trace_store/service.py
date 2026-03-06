"""Trace event persistence built on canonical Event model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from data_models import Event, EventType
from observability import sanitize_payload


@dataclass
class TraceStoreConfig:
    """Trace storage configuration."""

    storage_path: str = "/tmp/rd_agent_trace/events.jsonl"


class TraceStore:
    """Append-only JSONL trace event store."""

    def __init__(self, config: TraceStoreConfig) -> None:
        self._config = config
        self._path = Path(config.storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.touch()

    def append_event(self, event: Event) -> None:
        event_dict = event.to_dict()
        event_dict["payload"] = sanitize_payload(event_dict.get("payload", {}))
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event_dict, sort_keys=True) + "\n")

    def query_events(
        self,
        run_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
    ) -> List[Event]:
        events: List[Event] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                event = Event.from_dict(json.loads(line))
                if run_id is not None and event.run_id != run_id:
                    continue
                if event_type is not None and event.event_type != event_type:
                    continue
                events.append(event)
        return events
