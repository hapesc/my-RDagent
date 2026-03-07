"""LLM adapter with provider abstraction and structured output retries."""

from __future__ import annotations

import dataclasses
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Protocol, Type, TypeVar

from service_contracts import ModelSelectorConfig

T = TypeVar("T")

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)
_JSON_BLOCK_UNCLOSED_RE = re.compile(r"```(?:json)?\s*\n?(.*)", re.DOTALL)
_log = logging.getLogger(__name__)


class LLMProvider(Protocol):
    """Provider interface for text completion."""

    def complete(self, prompt: str, model_config: Optional[ModelSelectorConfig] = None) -> str:
        ...


class MockLLMProvider:
    """Deterministic mock provider for testing structured outputs."""

    def __init__(self, responses: Optional[List[str]] = None) -> None:
        self._responses = list(responses or [])

    @staticmethod
    def _extract_section(prompt: str, legacy_prefix: str, section_header: str) -> str:
        if legacy_prefix and legacy_prefix in prompt:
            return prompt.split(legacy_prefix, 1)[1].split("\n")[0].strip()
        if section_header in prompt:
            after = prompt.split(section_header, 1)[1]
            return after.split("\n")[0].strip()
        return ""

    def complete(self, prompt: str, model_config: Optional[ModelSelectorConfig] = None) -> str:
        def _metadata_tokens() -> List[str]:
            if model_config is None:
                return []
            tokens: List[str] = []
            if model_config.provider:
                tokens.append(f"provider:{model_config.provider}")
            if model_config.model:
                tokens.append(f"model:{model_config.model}")
            if model_config.temperature is not None:
                tokens.append(f"temperature:{model_config.temperature}")
            if model_config.max_tokens is not None:
                tokens.append(f"max_tokens:{model_config.max_tokens}")
            return tokens

        if self._responses:
            return self._responses.pop(0)

        prompt_lower = prompt.lower()
        is_merge = "research synthesizer" in prompt_lower or "completed traces" in prompt_lower
        if is_merge:
            return json.dumps(
                {
                    "summary": "Merged experiment design",
                    "constraints": ["merged-constraint-1", "merged-constraint-2"],
                    "virtual_score": 0.8,
                    "implementation_steps": ["merged step 1", "merged step 2"],
                }
            )

        is_proposal = "proposal:" in prompt or "`virtual_score`" in prompt
        is_coding = "coding:" in prompt or "`artifact_id`" in prompt
        is_feedback = "feedback:" in prompt or "`acceptable`" in prompt

        if is_proposal:
            summary = self._extract_section(prompt, "proposal:", "## Task\n") or "mock-proposal"
            constraints = ["llm-structured"] + _metadata_tokens()
            return json.dumps(
                {
                    "summary": summary,
                    "constraints": constraints,
                    "virtual_score": 0.5,
                }
            )
        if is_coding:
            summary = self._extract_section(prompt, "coding:", "## Research Proposal\n") or "mock-code"
            suffix = ""
            if model_config is not None and model_config.model:
                suffix = f" [model={model_config.model}]"
            return json.dumps(
                {
                    "artifact_id": "artifact-llm",
                    "description": f"{summary}{suffix}",
                    "location": "/tmp/rd_agent_workspace",
                }
            )
        if is_feedback:
            hypothesis = self._extract_section(prompt, "feedback:", "- Hypothesis: ")
            execution = self._extract_section(prompt, "", "- Execution: ")
            score = self._extract_section(prompt, "", "- Score: ")
            parts = [p for p in [hypothesis, execution, score] if p]
            reason = "; ".join(parts) if parts else "mock-feedback"
            if model_config is not None and model_config.model:
                reason = f"{reason};model={model_config.model}"
            return json.dumps(
                {
                    "decision": True,
                    "acceptable": True,
                    "reason": reason,
                    "observations": "llm-observation",
                    "code_change_summary": "llm-summary",
                }
            )

        # FC-3 Structured Feedback
        is_structured_feedback = "structured feedback" in prompt_lower or ("`execution`" in prompt and "`code`" in prompt and "`reasoning`" in prompt)
        if is_structured_feedback:
            return json.dumps({
                "execution": "Mock execution status: passed",
                "return_checking": "Mock return check: values consistent",
                "code": "Mock code review: clean implementation",
                "final_decision": True,
                "reasoning": "Mock reasoning: all checks passed",
            })

        # FC-3 Reasoning Stages (check more specific patterns first)
        is_analysis = "`strengths`" in prompt or "`weaknesses`" in prompt
        if is_analysis:
            return json.dumps(
                {
                    "strengths": ["Mock strength 1", "Mock strength 2"],
                    "weaknesses": ["Mock weakness 1"],
                    "current_performance": "Mock analysis",
                    "key_observations": "Mock observation",
                }
            )

        is_problem = "`severity`" in prompt or "`affected_component`" in prompt
        if is_problem:
            return json.dumps(
                {
                    "problem": "Mock problem identified",
                    "severity": "High",
                    "evidence": "Mock evidence",
                    "affected_component": "Mock component",
                }
            )

        is_hypothesis = "`mechanism`" in prompt or "`testable_prediction`" in prompt
        if is_hypothesis:
            return json.dumps(
                {
                    "hypothesis": "Mock hypothesis",
                    "mechanism": "Mock mechanism",
                    "expected_improvement": "Mock improvement",
                    "testable_prediction": "Mock prediction",
                }
            )

        # FC-1 Planning Strategy
        is_planning = "`strategy_name`" in prompt and "`method_selection`" in prompt
        if is_planning:
            return json.dumps(
                {
                    "strategy_name": "balanced_exploration",
                    "method_selection": "targeted_improvement",
                    "exploration_weight": 0.6,
                    "reasoning": "Mock planning strategy based on current progress",
                }
            )

        # FC-4 Hypothesis Modification
        is_hyp_mod = "`modified_hypothesis`" in prompt and "`modification_type`" in prompt
        if is_hyp_mod:
            return json.dumps(
                {
                    "modified_hypothesis": "Mock modified hypothesis",
                    "modification_type": "modify",
                    "source_hypothesis": "Mock source hypothesis",
                    "reasoning": "Mock modification reasoning",
                }
            )

        is_experiment = "`implementation_steps`" in prompt
        if is_experiment:
            return json.dumps(
                {
                    "summary": "Mock experiment design",
                    "constraints": ["constraint-1", "constraint-2"],
                    "virtual_score": 0.7,
                    "implementation_steps": ["step 1", "step 2", "step 3"],
                }
            )

        is_virtual_eval = "`rankings`" in prompt or "`selected_indices`" in prompt
        if is_virtual_eval:
            candidates = 5
            if "candidate" in prompt_lower:
                match = re.search(r"(\d+)\s*candidate", prompt_lower)
                if match:
                    candidates = int(match.group(1))
            rankings = list(range(candidates))
            selected_count = max(1, candidates // 2)
            selected_indices = list(range(selected_count))
            return json.dumps(
                {
                    "rankings": rankings,
                    "reasoning": "Mock ranking strategy",
                    "selected_indices": selected_indices,
                }
            )

        return json.dumps({"message": "ok"})


@dataclass
class LLMAdapterConfig:
    """Adapter configuration."""

    max_retries: int = 2


class LLMAdapter:
    """Adapter that parses structured JSON outputs with retries."""

    def __init__(self, provider: LLMProvider, config: Optional[LLMAdapterConfig] = None) -> None:
        self._provider = provider
        self._config = config or LLMAdapterConfig()

    def _build_schema_hint(self, schema_cls: Type) -> str:
        """Build JSON schema hint from a dataclass with from_dict."""
        if not dataclasses.is_dataclass(schema_cls):
            return ""
        example: dict = {}
        for f in dataclasses.fields(schema_cls):
            ann = str(f.type)
            if ann in ("str", "<class 'str'>"):
                example[f.name] = "string"
            elif ann in ("float", "<class 'float'>"):
                example[f.name] = 0.0
            elif ann in ("bool", "<class 'bool'>"):
                example[f.name] = True
            elif "List[str]" in ann:
                example[f.name] = ["string"]
            elif "List[int]" in ann:
                example[f.name] = [0]
            elif "List[float]" in ann:
                example[f.name] = [0.0]
            else:
                example[f.name] = "value"
        return json.dumps(example, indent=2)

    def _enhance_prompt(self, prompt: str, schema_cls: Type) -> str:
        schema_hint = self._build_schema_hint(schema_cls)
        if not schema_hint:
            return prompt
        return (
            f"{prompt}\n\n"
            f"--- OUTPUT FORMAT ---\n"
            f"Respond with a single raw JSON object. "
            f"Do NOT wrap in ```json``` or any markdown. "
            f"Do NOT include explanation before or after the JSON.\n"
            f"Schema:\n{schema_hint}"
        )

    @staticmethod
    def _extract_json(raw: str) -> str:
        """Strip markdown code fences if present, including unclosed fences (truncated output)."""
        match = _JSON_BLOCK_RE.search(raw)
        if match:
            return match.group(1).strip()
        # Handle unclosed fence (e.g. output truncated before closing ```)
        match = _JSON_BLOCK_UNCLOSED_RE.search(raw)
        if match:
            return match.group(1).strip()
        return raw.strip()

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        model_config: Optional[ModelSelectorConfig] = None,
    ) -> T:
        last_error: Optional[Exception] = None
        max_retries = self._config.max_retries
        if model_config is not None and model_config.max_retries is not None:
            max_retries = model_config.max_retries
        attempts = max_retries + 1

        enhanced = self._enhance_prompt(prompt, schema_cls)

        for attempt in range(attempts):
            raw = self._provider.complete(enhanced, model_config=model_config)
            try:
                cleaned = self._extract_json(raw)
                payload = json.loads(cleaned)
                if not hasattr(schema_cls, "from_dict"):
                    raise TypeError(f"schema_cls missing from_dict: {schema_cls}")
                converter = getattr(schema_cls, "from_dict")
                parsed = converter(payload)
                return parsed
            except Exception as exc:
                _log.warning("parse attempt %d/%d failed: %s  raw[:200]=%s",
                             attempt + 1, attempts, exc, (raw or "")[:200])
                last_error = exc

        raise ValueError(f"structured output parse failed after {attempts} attempts: {last_error}")
