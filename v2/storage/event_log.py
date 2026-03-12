from __future__ import annotations

import json
from pathlib import Path

from v2.storage.protocols import EventLogStore


class JSONLEventLog(EventLogStore):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.touch()

    def append(self, event: dict) -> None:
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def read_all(self) -> list[dict]:
        events: list[dict] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))
        return events


__all__ = ["JSONLEventLog"]
