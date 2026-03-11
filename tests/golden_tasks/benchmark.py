from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm import LLMAdapter, LLMAdapterConfig
from llm.codegen.quality_gate import CodegenQualityGate
from llm.providers.litellm_provider import LiteLLMProvider
from service_contracts import ModelSelectorConfig

GOLDEN_TASKS_DIR = Path(__file__).parent
_PLACEHOLDER_TOKENS = ("todo", "tbd", "placeholder", "lorem ipsum", "{{", "}}", "fill in")

# ---------------------------------------------------------------------------
# Benchmark-specific short prompts
# ---------------------------------------------------------------------------
# These are optimised purely for single-round through-rate.  They are NOT
# the production prompts used by the CoSTEER loop – those live in
# llm/prompts.py and scenarios/*/prompts.py.
# ---------------------------------------------------------------------------

_QUANT_BENCHMARK_PROMPT = """\
You are a quantitative developer.  Implement the factor described below as \
a single Python function.

TASK: {task_summary}

SCHEMA
------
Input DataFrame columns: date (datetime), stock_id (str), open, high, low, \
close, volume (all float).
Output DataFrame: exactly three columns – date, stock_id, factor_value (float).

RULES
-----
1. Define `def compute_factor(df: pd.DataFrame) -> pd.DataFrame:`.
2. Import only pandas and numpy.  No os/subprocess/requests/sys.
3. No look-ahead bias – never use `.shift(-n)`.
4. Handle NaN from rolling/pct_change.
5. Return ONLY one fenced python code block.  No JSON wrapper, no prose.

REFERENCE
---------
Momentum example: `df.groupby('stock_id')['close'].pct_change(5)`
Volatility example: `df.groupby('stock_id')['close'].pct_change().rolling(20).std()`
"""

_DS_BENCHMARK_PROMPT = """\
You are a data scientist.  Write one complete, runnable Python script for \
the task below.

TASK: {task_summary}

RULES
-----
1. The script must be self-contained (load/generate data, train, evaluate).
2. Write evaluation metrics to a file called `metrics.json` using `json.dump`.
3. Use scikit-learn or standard libraries only.
4. Do NOT use placeholders, TODOs, or fake metrics.
5. Keep the code concise: under 60 lines, no comments, no docstrings.
6. Return ONLY one fenced python code block.  No JSON wrapper, no prose.
"""

_SYNTHETIC_BENCHMARK_PROMPT = """\
You are a research analyst.  Write a structured markdown report for the \
task below.

TASK: {task_summary}

FORMAT
------
Use these headings (exactly):
  ## Findings
  ## Methodology
  ## Conclusion

Under ## Findings, use numbered items with specific quantitative evidence \
(numbers, percentages, ranges).  Do NOT just restate the task.

RULES
-----
1. Minimum 300 words.
2. Include at least 3 quantitative claims (numbers, percentages, measurements).
3. No placeholder text, no "TODO", no generic summaries.
4. Return ONLY the markdown report.  No fenced code block wrapper.
"""

_BENCHMARK_PROMPTS: dict[str, str] = {
    "quant": _QUANT_BENCHMARK_PROMPT,
    "data_science": _DS_BENCHMARK_PROMPT,
    "synthetic_research": _SYNTHETIC_BENCHMARK_PROMPT,
}

# Scenario-specific max_tokens overrides (default is 4096)
_SCENARIO_MAX_TOKENS: dict[str, int] = {
    "quant": 4096,
    "data_science": 4096,
    "synthetic_research": 4096,
}


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
        max_tokens=4096,
        max_retries=0,
    )
    return adapter, config


def _build_benchmark_prompt(golden_task: dict[str, Any]) -> str:
    """Build a short, benchmark-specific prompt for the given golden task."""
    scenario = str(golden_task["scenario"])
    template = _BENCHMARK_PROMPTS.get(scenario)
    if template is None:
        raise ValueError(f"No benchmark prompt template for scenario: {scenario}")
    return template.format(task_summary=golden_task["task_summary"])


def run_single_round(
    golden_task: dict[str, Any], llm_adapter: LLMAdapter, model_config: ModelSelectorConfig
) -> BenchmarkResult:
    scenario = str(golden_task["scenario"])
    task_id = str(golden_task["task_id"])
    artifact = ""
    try:
        prompt = _build_benchmark_prompt(golden_task)

        # Apply scenario-specific max_tokens override
        max_tokens = _SCENARIO_MAX_TOKENS.get(scenario, 4096)
        effective_config = ModelSelectorConfig(
            provider=model_config.provider,
            model=model_config.model,
            temperature=model_config.temperature,
            max_tokens=max_tokens,
            max_retries=model_config.max_retries,
        )

        raw_output = llm_adapter.complete(prompt, model_config=effective_config)
        gate_result = CodegenQualityGate(scenario).evaluate(raw_output)
        artifact = (gate_result.extracted_code or "").strip()
    except Exception as exc:
        return BenchmarkResult(
            task_id=task_id,
            scenario=scenario,
            passed=False,
            reasons=[f"generation failed: {type(exc).__name__}: {exc}"],
            artifact=artifact,
        )

    reasons = list(gate_result.reasons)
    reasons.extend(
        evaluate_expected_properties(artifact=artifact, expected_properties=golden_task["expected_properties"])
    )
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
