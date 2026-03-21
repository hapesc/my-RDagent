"""Self-contained merge helper abstraction for V3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MergeDesign:
    summary: str


class MergeAdapter(Protocol):
    def merge(self, traces: list[dict], task_summary: str, scenario_name: str) -> MergeDesign: ...


class SimpleTraceMerger:
    """Minimal synthesis helper used by the standalone V3 surface."""

    def merge(self, traces: list[dict], task_summary: str, scenario_name: str) -> MergeDesign:
        summaries: list[str] = []
        for trace in traces:
            design = trace.get("design", {})
            if isinstance(design, dict):
                summaries.append(str(design.get("summary", "")))
            else:
                summaries.append(str(design))
        merged = " | ".join(part for part in summaries if part) or f"Synthesis for {scenario_name}: {task_summary}"
        return MergeDesign(summary=merged)
