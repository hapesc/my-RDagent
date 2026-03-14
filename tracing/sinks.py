"""Primary and mirror sink abstractions for benchmark tracing."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from data_models import Event, EventType
from observability import sanitize_payload
from trace_store.service import TraceStore

_log = logging.getLogger(__name__)


class TraceSink(Protocol):
    def append_event(self, event: Event) -> None: ...


class LangSmithClient(Protocol):
    def create_event(self, **kwargs: Any) -> None: ...


@dataclass
class JsonlMirrorSink:
    store: TraceStore

    def append_event(self, event: Event) -> None:
        self.store.append_event(event)


@dataclass
class LangSmithPrimarySink:
    tracing_config: Any
    client: LangSmithClient | None = None

    def append_event(self, event: Event) -> None:
        payload = sanitize_payload(event.payload)
        if self.client is None:
            _log.warning("LangSmith tracing enabled but no client is configured; dropping event %s", event.event_id)
            return
        try:
            self.client.create_event(
                name=event.event_type.value,
                run_id=event.run_id,
                metadata={
                    "event_id": event.event_id,
                    "timestamp": event.to_dict()["timestamp"],
                    "branch_id": event.branch_id,
                    "loop_index": event.loop_index,
                    "step_name": event.step_name,
                    **payload,
                },
            )
        except Exception:
            _log.exception("LangSmith primary sink failed for event %s", event.event_id)
            raise


@dataclass
class TraceSinkFanout:
    primary: TraceSink
    mirrors: tuple[TraceSink, ...] = ()

    def append_event(self, event: Event) -> None:
        """Append to the primary sink first; mirror failures are isolated."""
        self.primary.append_event(event)
        for mirror in self.mirrors:
            try:
                mirror.append_event(event)
            except Exception as exc:
                _log.warning("Mirror trace sink failed: %s", exc)


@dataclass
class RecorderSinkAdapter:
    sink: TraceSink
    event_type: EventType = EventType.TRACE_RECORDED
    branch_id: str = "main"

    def record(
        self,
        *,
        run_id: str,
        scenario: str,
        loop_iteration: int,
        last_completed_node: str | None = None,
        next_node: str | None = None,
        checkpoint_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        payload_dict = dict(payload or {})
        branch_id = str(payload_dict.pop("branch_id", self.branch_id))
        event = Event(
            event_id=f"event-{uuid.uuid4().hex}",
            run_id=run_id,
            branch_id=branch_id,
            loop_index=loop_iteration,
            step_name=last_completed_node or "unknown",
            event_type=self.event_type,
            payload={
                "scenario": scenario,
                "next_node": next_node,
                "checkpoint_id": checkpoint_id,
                **payload_dict,
            },
        )
        self.sink.append_event(event)
