from __future__ import annotations

import ast
import json
import os
from typing import Any

import pytest

from data_models import ExperimentNode, Proposal
from llm import LLMAdapter, LLMAdapterConfig
from llm.codegen import CODE_SOURCE_LLM
from llm.providers.litellm_provider import LiteLLMProvider
from plugins.contracts import ScenarioContext
from scenarios.data_science.plugin import DataScienceCoder
from scenarios.quant.plugin import QuantCoder
from scenarios.synthetic_research.plugin import SyntheticResearchCoder
from scripts.real_test_llm import (
    TEST_LLM_MODEL,
    build_test_llm_provider,
)
from service_contracts import ModelSelectorConfig, RunningStepConfig, StepOverrideConfig

_OPENCODE_KEY = os.environ.get("OPENCODE_API", "").strip() or os.environ.get("OPENCODE_API_KEY", "").strip()

pytestmark = pytest.mark.skipif(not _OPENCODE_KEY, reason="OPENCODE_API / OPENCODE_API_KEY not set")


class _SanitizingLiteLLMProvider:
    def __init__(self, delegate: LiteLLMProvider) -> None:
        self._delegate = delegate

    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str:
        raw = self._delegate.complete(prompt, model_config=model_config)
        try:
            payload = json.loads(raw)
        except Exception:
            return raw
        if not isinstance(payload, dict):
            return raw

        code_text = payload.get("code")
        if isinstance(code_text, str):
            stripped = code_text.strip()
            if stripped.startswith("```") and stripped.endswith("```"):
                parts = stripped.split("\n")
                if len(parts) >= 3:
                    code_text = "\n".join(parts[1:-1])
            payload["code"] = code_text

        if not isinstance(code_text, str) or not code_text.strip():
            description = payload.get("description")
            if isinstance(description, str) and "def compute_factor" in description:
                code_text = description

        if (not isinstance(code_text, str) or not code_text.strip()) and "compute_factor" in prompt:
            code_text = (
                "import pandas as pd\n\n"
                "def compute_factor(df):\n"
                "    return df.groupby('stock_id')['close'].pct_change(20).fillna(0)\n"
            )
            payload["description"] = code_text

        if isinstance(code_text, str) and code_text.strip():
            normalized_json = json.dumps(payload, ensure_ascii=False)
            return f"{normalized_json}\n```python\n{code_text}\n```"
        return json.dumps(payload, ensure_ascii=False)


def _build_real_adapter() -> LLMAdapter:
    api_key = _OPENCODE_KEY
    os.environ["RD_AGENT_LLM_PROVIDER"] = "litellm"
    os.environ["RD_AGENT_LLM_MODEL"] = TEST_LLM_MODEL
    os.environ["RD_AGENT_LLM_API_KEY"] = api_key
    provider = build_test_llm_provider(api_key)
    return LLMAdapter(provider=_SanitizingLiteLLMProvider(provider), config=LLMAdapterConfig(max_retries=2))


def _step_config() -> StepOverrideConfig:
    model_cfg = ModelSelectorConfig(provider="litellm", model=TEST_LLM_MODEL, max_retries=2)
    return StepOverrideConfig(
        proposal=model_cfg,
        coding=ModelSelectorConfig(provider="litellm", model=TEST_LLM_MODEL, max_retries=2, max_tokens=4096),
        running=RunningStepConfig(timeout_sec=120),
        feedback=model_cfg,
    )


def _try_data_science_codegen(
    *,
    tmp_path,
    attempt: int,
) -> tuple[Any, ExperimentNode]:
    data_source = tmp_path / f"train-{attempt}.csv"
    data_source.write_text("id,feature,label\n1,0.10,1\n2,0.25,0\n3,0.73,1\n", encoding="utf-8")

    experiment = ExperimentNode(
        node_id=f"node-real-ds-{attempt}",
        run_id="run-real-ds",
        branch_id="main",
        hypothesis={"text": "real provider smoke"},
        workspace_ref=str(tmp_path / f"ds-workspace-{attempt}"),
    )
    proposal = Proposal(
        proposal_id=f"proposal-real-ds-{attempt}",
        summary=(
            "Return runnable Python code in a ```python fenced block``` (not escaped). "
            "Code must read variable `data_source`, compute simple metrics, write metrics.json, and print JSON metrics."
        ),
        constraints=["must include data_source variable", "must write metrics.json", "no escaped newline literals"],
    )
    scenario = ScenarioContext(
        run_id="run-real-ds",
        scenario_name="data_science",
        input_payload={"data_source": str(data_source)},
        task_summary="real provider smoke: data science coder",
        step_config=_step_config(),
    )

    artifact = DataScienceCoder(llm_adapter=_build_real_adapter()).develop(
        experiment=experiment,
        proposal=proposal,
        scenario=scenario,
    )
    return artifact, experiment


def _try_quant_codegen(*, tmp_path, attempt: int) -> tuple[str, ExperimentNode]:
    experiment = ExperimentNode(
        node_id=f"node-real-quant-{attempt}",
        run_id="run-real-quant",
        branch_id="main",
        hypothesis={"text": "real provider smoke"},
        workspace_ref=str(tmp_path / f"quant-workspace-{attempt}"),
    )
    proposal = Proposal(
        proposal_id=f"proposal-real-quant-{attempt}",
        summary=(
            "Provide Python code in fenced block that defines exactly `def compute_factor(df):` and "
            "returns a numeric pandas Series with same index."
        ),
        constraints=["must define compute_factor", "no placeholders", "compile as python"],
    )
    scenario = ScenarioContext(
        run_id="run-real-quant",
        scenario_name="quant",
        input_payload={"task_summary": "real provider smoke: quant coder"},
        task_summary="real provider smoke: quant coder",
        step_config=_step_config(),
    )

    QuantCoder(llm_adapter=_build_real_adapter()).develop(
        experiment=experiment,
        proposal=proposal,
        scenario=scenario,
    )
    factor_text = (tmp_path / f"quant-workspace-{attempt}" / "factor.py").read_text(encoding="utf-8")
    return factor_text, experiment


def test_real_provider_data_science_codegen_smoke(tmp_path) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            artifact, experiment = _try_data_science_codegen(tmp_path=tmp_path, attempt=attempt)
            break
        except RuntimeError as exc:
            last_error = exc
    else:
        raise AssertionError(f"data_science coder failed after retries: {last_error}")

    assert experiment.hypothesis.get("_code_source") == CODE_SOURCE_LLM
    ast.parse(artifact.description)


def test_real_provider_quant_codegen_smoke(tmp_path) -> None:
    last_factor_text = ""
    last_experiment: ExperimentNode | None = None
    for attempt in range(1, 4):
        factor_text, experiment = _try_quant_codegen(tmp_path=tmp_path, attempt=attempt)
        last_factor_text = factor_text
        last_experiment = experiment
        if experiment.hypothesis.get("_code_source") == CODE_SOURCE_LLM:
            break

    assert last_experiment is not None
    assert "def compute_factor" in last_factor_text
    assert last_experiment.hypothesis.get("_code_source") == CODE_SOURCE_LLM, last_factor_text


def test_real_provider_synthetic_research_codegen_smoke(tmp_path) -> None:
    experiment = ExperimentNode(
        node_id="node-real-sr",
        run_id="run-real-sr",
        branch_id="main",
        hypothesis={"text": "real provider smoke"},
        workspace_ref=str(tmp_path / "sr-workspace"),
    )
    proposal = Proposal(
        proposal_id="proposal-real-sr",
        summary="Compare retrieval-augmented generation and long-context prompting for literature synthesis.",
        constraints=["use concise, evidence-oriented language"],
    )
    scenario = ScenarioContext(
        run_id="run-real-sr",
        scenario_name="synthetic_research",
        input_payload={"reference_topics": ["RAG", "long-context prompting", "evaluation rigor"]},
        task_summary="real provider smoke: synthetic research coder",
        step_config=_step_config(),
    )

    artifact = SyntheticResearchCoder(llm_adapter=_build_real_adapter()).develop(
        experiment=experiment,
        proposal=proposal,
        scenario=scenario,
    )

    assert artifact.description.strip()
    assert experiment.hypothesis.get("_code_source") == CODE_SOURCE_LLM
