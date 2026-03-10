from __future__ import annotations

import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

CODE_SOURCE_LLM = "llm"
CODE_SOURCE_TEMPLATE = "template"
CODE_SOURCE_FAILED = "failed"
CODE_SOURCE_REJECTED_SAFETY = "rejected_safety"
CODE_SOURCE_REJECTED_PLACEHOLDER = "rejected_placeholder"


def emit_code_source_event(code_source: str, scenario: str, details: dict[str, Any]) -> None:
    event_details = dict(details or {})
    log_details = {**event_details, "code_source": code_source, "scenario": scenario}

    try:
        from data_models import Event, EventType
    except (ImportError, AttributeError):
        logger.exception("Failed to import trace event dependencies for code_source event")
        logger.info(
            "code_source_event: source=%s scenario=%s details=%s",
            code_source,
            scenario,
            log_details,
        )
        return

    event = Event(
        event_id=f"event-{uuid.uuid4().hex}",
        run_id=str(event_details.get("run_id", "codegen")),
        branch_id=str(event_details.get("branch_id", "main")),
        loop_index=_coerce_loop_index(event_details.get("loop_index", 0)),
        step_name=str(event_details.get("step_name", "codegen")),
        event_type=EventType.TRACE_RECORDED,
        payload=log_details,
    )

    trace_storage_path = os.getenv("AGENTRD_TRACE_STORAGE_PATH", "").strip()
    if trace_storage_path:
        try:
            from trace_store.service import TraceStore, TraceStoreConfig

            TraceStore(TraceStoreConfig(storage_path=trace_storage_path)).append_event(event)
            return
        except (ImportError, AttributeError, OSError):
            logger.exception("Failed to emit code_source event via TraceStore")

    sqlite_path = os.getenv("AGENTRD_SQLITE_PATH", "").strip()
    if sqlite_path:
        try:
            from core.storage import SQLiteMetadataStore, SQLiteStoreConfig

            SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path)).append_event(event)
            return
        except (ImportError, AttributeError, OSError):
            logger.exception("Failed to emit code_source event via SQLiteMetadataStore")

    logger.info(
        "code_source_event: source=%s scenario=%s details=%s",
        code_source,
        scenario,
        log_details,
    )


def _coerce_loop_index(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "CODE_SOURCE_FAILED",
    "CODE_SOURCE_LLM",
    "CODE_SOURCE_REJECTED_PLACEHOLDER",
    "CODE_SOURCE_REJECTED_SAFETY",
    "CODE_SOURCE_TEMPLATE",
    "emit_code_source_event",
]
