from __future__ import annotations

import json
import logging
import logging.config
from collections.abc import MutableMapping
from datetime import UTC, datetime
from typing import Any, cast

from observability.redaction import sanitize_payload

_STANDARD_RECORD_FIELDS = frozenset(vars(logging.makeLogRecord({})).keys())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        extra_fields = self._extract_extra_fields(record)
        if extra_fields:
            payload.update(extra_fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["exception"] = record.exc_text

        return json.dumps(sanitize_payload(payload), ensure_ascii=False)

    def _extract_extra_fields(self, record: logging.LogRecord) -> dict[str, Any]:
        record_dict = cast(MutableMapping[str, Any], record.__dict__)
        return {
            key: value
            for key, value in record_dict.items()
            if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_")
        }


def configure_logging(level: str = "INFO", json_format: bool = True) -> None:
    formatter_name = "json" if json_format else "standard"
    normalized_level = level.upper()

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "observability.logging_config.JsonFormatter",
                },
                "standard": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
            },
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "level": normalized_level,
                    "formatter": formatter_name,
                    "stream": "ext://sys.stderr",
                }
            },
            "root": {
                "level": normalized_level,
                "handlers": ["stderr"],
            },
            "loggers": {
                "uvicorn": {
                    "level": normalized_level,
                    "handlers": ["stderr"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": normalized_level,
                    "handlers": ["stderr"],
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": normalized_level,
                    "handlers": ["stderr"],
                    "propagate": False,
                },
            },
        }
    )
