"""Self-contained merge helper abstraction for V3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MergeDesign:
    summary: str
    operation: str = "select"
    source_branch_ids: tuple[str, ...] = ()
    component_analysis: str = ""
    holdout_score: float | None = None


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


class LLMTraceMerger:
    """Phase 27 merger that chooses between select/modify/create synthesis modes."""

    def merge(self, traces: list[dict], task_summary: str, scenario_name: str) -> MergeDesign:
        if not traces:
            return MergeDesign(
                summary=f"No traces to merge for {scenario_name}",
                operation="select",
            )
        component_analysis = self._analyze_components(traces)
        operation = self._determine_operation(traces)
        synthesis = self._synthesize(traces, operation, task_summary, scenario_name)
        source_ids = tuple(str(trace.get("branch_id", f"trace-{index}")) for index, trace in enumerate(traces))
        return MergeDesign(
            summary=synthesis,
            operation=operation,
            source_branch_ids=source_ids,
            component_analysis=component_analysis,
        )

    def _analyze_components(self, traces: list[dict]) -> str:
        parts: list[str] = []
        for index, trace in enumerate(traces):
            components = trace.get("components", {})
            strong = [name for name, score in components.items() if isinstance(score, (int, float)) and score >= 0.7]
            parts.append(f"trace-{index}: {', '.join(strong) if strong else 'none'}")
        return "; ".join(parts)

    def _determine_operation(self, traces: list[dict]) -> str:
        if len(traces) == 1:
            return "select"
        strengths: list[set[str]] = []
        all_strengths: set[str] = set()
        for trace in traces:
            components = trace.get("components", {})
            current = {name for name, score in components.items() if isinstance(score, (int, float)) and score >= 0.7}
            strengths.append(current)
            all_strengths |= current
        if len(strengths) >= 2:
            overlap = strengths[0] & strengths[1]
            if all_strengths and len(overlap) < max(1, len(all_strengths) // 2):
                return "create"
            return "modify"
        return "select"

    def _synthesize(
        self,
        traces: list[dict],
        operation: str,
        task_summary: str,
        scenario_name: str,
    ) -> str:
        summaries: list[str] = []
        for trace in traces:
            design = trace.get("design", {})
            if isinstance(design, dict):
                summaries.append(str(design.get("summary", "")))
            else:
                summaries.append(str(design))
        prefix = {"select": "Selected", "modify": "Modified", "create": "Synthesized"}
        action = prefix.get(operation, "Merged")
        joined = " + ".join(part for part in summaries if part) or task_summary
        return f"{action} for {scenario_name}: {joined}"

__all__ = [
    "LLMTraceMerger",
    "MergeAdapter",
    "MergeDesign",
    "SimpleTraceMerger",
]
