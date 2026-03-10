from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm import CodeDraft, LLMAdapter, LLMAdapterConfig, coding_prompt
from llm.providers.litellm_provider import LiteLLMProvider
from scenarios.quant.prompts import DATA_SCHEMA_DESCRIPTION, FACTOR_CODE_SYSTEM_PROMPT, FACTOR_CODE_USER_TEMPLATE
from service_contracts import ModelSelectorConfig

GOLDEN_TASKS_DIR = Path(__file__).parent
_PLACEHOLDER_TOKENS = ("todo", "tbd", "placeholder", "lorem ipsum", "{{", "}}", "fill in")


@dataclass(frozen=True)
class BenchmarkResult:
    task_id: str
    scenario: str
    passed: bool
    reasons: list[str]
    artifact: str


def load_golden_tasks(scenario: str | None = None) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for path in sorted(GOLDEN_TASKS_DIR.glob("*.json")):
        if path.name == "baseline.json":
            continue
        task = json.loads(path.read_text(encoding="utf-8"))
        if scenario is None or task["scenario"] == scenario:
            tasks.append(task)
    return tasks


def resolve_benchmark_credentials() -> tuple[str, str]:
    explicit_model = os.environ.get("BENCHMARK_LLM_MODEL")
    if explicit_model:
        if explicit_model.startswith("gemini/"):
            return os.environ.get("GEMINI_API_KEY", ""), explicit_model
        if explicit_model.startswith(("gpt-", "openai/")):
            return os.environ.get("OPENAI_API_KEY", ""), explicit_model.removeprefix("openai/")
        return os.environ.get("BENCHMARK_LLM_API_KEY", ""), explicit_model

    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"], "gemini/gemini-2.5-flash"
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"], "gpt-4o-mini"
    return "", "gpt-4o-mini"


def create_benchmark_llm_adapter() -> tuple[LLMAdapter, ModelSelectorConfig]:
    api_key, model = resolve_benchmark_credentials()
    if not api_key:
        raise RuntimeError("A supported benchmark API key is required to run the golden benchmark")

    temperature = float(os.environ.get("BENCHMARK_LLM_TEMPERATURE", "0.0"))
    base_url = os.environ.get("BENCHMARK_LLM_BASE_URL")
    provider = LiteLLMProvider(api_key=api_key, model=model, base_url=base_url)
    adapter = LLMAdapter(provider=provider, config=LLMAdapterConfig(max_retries=0))
    config = ModelSelectorConfig(
        provider="litellm",
        model=model,
        temperature=temperature,
        max_tokens=2048,
        max_retries=0,
    )
    return adapter, config


def run_single_round(golden_task: dict[str, Any], llm_adapter: LLMAdapter, model_config: ModelSelectorConfig) -> BenchmarkResult:
    scenario = str(golden_task["scenario"])
    task_id = str(golden_task["task_id"])
    artifact = ""
    try:
        if scenario == "quant":
            prompt = (
                FACTOR_CODE_SYSTEM_PROMPT
                + "\n\n"
                + FACTOR_CODE_USER_TEMPLATE.format(
                    factor_hypothesis=golden_task["task_summary"],
                    data_schema=DATA_SCHEMA_DESCRIPTION,
                )
            )
            draft, code = llm_adapter.generate_code(prompt, CodeDraft, model_config=model_config)
            artifact = code.strip() or draft.description.strip()
        else:
            prompt = coding_prompt(
                proposal_summary=str(golden_task["task_summary"]),
                constraints=[],
                experiment_node_id="golden-benchmark",
                workspace_ref="/tmp/golden-benchmark",
                scenario_name=scenario,
            )
            draft = llm_adapter.generate_structured(prompt, CodeDraft, model_config=model_config)
            artifact = draft.description.strip()
    except Exception as exc:
        return BenchmarkResult(
            task_id=task_id,
            scenario=scenario,
            passed=False,
            reasons=[f"generation failed: {type(exc).__name__}: {exc}"],
            artifact=artifact,
        )

    reasons = evaluate_expected_properties(artifact=artifact, expected_properties=golden_task["expected_properties"])
    return BenchmarkResult(
        task_id=task_id,
        scenario=scenario,
        passed=not reasons,
        reasons=reasons,
        artifact=artifact,
    )


def evaluate_expected_properties(artifact: str, expected_properties: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    artifact_lower = artifact.lower()

    if expected_properties.get("compiles"):
        try:
            compile(artifact, "<golden-artifact>", "exec")
        except SyntaxError as exc:
            reasons.append(f"compile failed: {exc.msg}")

    signature = expected_properties.get("has_signature")
    if signature and f"def {signature}" not in artifact:
        reasons.append(f"missing signature: {signature}")

    forbidden_imports = expected_properties.get("forbidden_imports_absent", [])
    for forbidden in forbidden_imports:
        if f"import {forbidden}" in artifact or f"from {forbidden} import" in artifact:
            reasons.append(f"forbidden import present: {forbidden}")

    if expected_properties.get("no_placeholder"):
        for token in _PLACEHOLDER_TOKENS:
            if token in artifact_lower:
                reasons.append(f"placeholder token present: {token}")
                break

    contains_all = expected_properties.get("contains_all_keywords", [])
    for keyword in contains_all:
        if keyword.lower() not in artifact_lower:
            reasons.append(f"missing required keyword: {keyword}")

    contains_any = expected_properties.get("contains_any_keyword", [])
    if contains_any and not any(keyword.lower() in artifact_lower for keyword in contains_any):
        reasons.append(f"missing any keyword from: {contains_any}")

    min_length_chars = expected_properties.get("min_length_chars")
    if min_length_chars and len(artifact) < int(min_length_chars):
        reasons.append(f"artifact too short: {len(artifact)} < {min_length_chars}")

    if expected_properties.get("has_structure"):
        lines = [line.strip() for line in artifact.splitlines() if line.strip()]
        has_heading = any(line.startswith("#") for line in lines)
        has_list = any(line.startswith(("1.", "2.", "-", "*")) for line in lines)
        if not (has_heading and has_list):
            reasons.append("structured text missing headings or list items")

    return reasons
