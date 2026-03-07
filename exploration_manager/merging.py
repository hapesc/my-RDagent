from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from llm.adapter import LLMAdapter
from llm.prompts import merge_traces_prompt
from llm.schemas import ExperimentDesign
from service_contracts import ModelSelectorConfig

_log = logging.getLogger(__name__)


class TraceMerger:
    def __init__(self, llm_adapter: LLMAdapter) -> None:
        self._llm_adapter = llm_adapter

    def merge(
        self,
        traces: List[Dict[str, Any]],
        task_summary: str,
        scenario_name: str,
        model_config: Optional[ModelSelectorConfig] = None,
    ) -> ExperimentDesign:
        if not traces:
            raise ValueError("Cannot merge empty traces list")

        if len(traces) == 1:
            trace = traces[0]
            design_data = trace.get("design", {})
            if isinstance(design_data, dict):
                return ExperimentDesign.from_dict(design_data)
            return ExperimentDesign(summary=str(design_data))

        trace_summaries = [self._format_trace(t, i) for i, t in enumerate(traces)]
        prompt = merge_traces_prompt(
            trace_summaries=trace_summaries,
            task_summary=task_summary,
            scenario_name=scenario_name,
        )
        result = self._llm_adapter.generate_structured(
            prompt,
            ExperimentDesign,
            model_config=model_config,
        )
        _log.info("Merged %d traces into design: %s", len(traces), result.summary[:60])
        return result

    @staticmethod
    def _format_trace(trace: Dict[str, Any], index: int) -> str:
        parts = []
        if "analysis" in trace:
            analysis = trace["analysis"]
            if isinstance(analysis, dict):
                parts.append(f"Analysis: {analysis.get('key_observations', str(analysis))}")
            else:
                parts.append(f"Analysis: {analysis}")
        if "problem" in trace:
            problem = trace["problem"]
            if isinstance(problem, dict):
                parts.append(f"Problem: {problem.get('problem', str(problem))}")
            else:
                parts.append(f"Problem: {problem}")
        if "hypothesis" in trace:
            hypothesis = trace["hypothesis"]
            if isinstance(hypothesis, dict):
                parts.append(f"Hypothesis: {hypothesis.get('hypothesis', str(hypothesis))}")
            else:
                parts.append(f"Hypothesis: {hypothesis}")
        if "design" in trace:
            design = trace["design"]
            if isinstance(design, dict):
                parts.append(f"Design: {design.get('summary', str(design))}")
            else:
                parts.append(f"Design: {design}")
        return "\n".join(parts) if parts else f"Trace {index + 1}: (no data)"
