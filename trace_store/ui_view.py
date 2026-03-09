"""UI-facing trace projection based on canonical Event model."""

from __future__ import annotations

from typing import Any

from data_models import Event


class TraceTimelineView:
    """Transforms trace events into timeline rows for UI rendering."""

    def build_rows(self, events: list[Event]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for event in sorted(events, key=lambda item: item.timestamp):
            rows.append(
                {
                    "event_id": event.event_id,
                    "run_id": event.run_id,
                    "branch_id": event.branch_id,
                    "loop_index": event.loop_index,
                    "step_name": event.step_name,
                    "event_type": event.event_type.value,
                    "timestamp": event.to_dict()["timestamp"],
                    "payload": event.payload,
                }
            )
        return rows
