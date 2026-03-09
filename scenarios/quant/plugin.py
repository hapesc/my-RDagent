"""Quant scenario plugin: factor mining loop via LLM + lightweight backtester."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from data_models import (
    CodeArtifact,
    ContextPack,
    ExecutionResult,
    ExperimentNode,
    FeedbackRecord,
    LoopState,
    Plan,
    Proposal,
    RunSession,
    Score,
    StepState,
)
from llm import (
    LLMAdapter,
    ProposalDraft,
)
from plugins.contracts import (
    Coder,
    ExperimentGenerator,
    FeedbackAnalyzer,
    PluginBundle,
    ProposalEngine,
    Runner,
    ScenarioContext,
    ScenarioPlugin,
    UsefulnessGateInput,
)
from service_contracts import ModelSelectorConfig, RunningStepConfig, ScenarioManifest, StepOverrideConfig

from .backtest import LightweightBacktester
from .constants import METRIC_THRESHOLDS
from .data_provider import QuantDataProvider
from .prompts import (
    DATA_SCHEMA_DESCRIPTION,
    FACTOR_CODE_SYSTEM_PROMPT,
    FACTOR_CODE_USER_TEMPLATE,
    FACTOR_PROPOSAL_SYSTEM_PROMPT,
    FACTOR_PROPOSAL_USER_TEMPLATE,
    FEEDBACK_ANALYSIS_TEMPLATE,
)

if TYPE_CHECKING:
    pass


def default_quant_step_overrides(timeout_sec: int = 60) -> StepOverrideConfig:
    return StepOverrideConfig(
        proposal=ModelSelectorConfig(provider="mock", model="quant-proposal-default", max_retries=2),
        coding=ModelSelectorConfig(
            provider="mock",
            model="quant-coding-default",
            max_retries=2,
            max_tokens=2048,
        ),
        running=RunningStepConfig(timeout_sec=timeout_sec),
        feedback=ModelSelectorConfig(provider="mock", model="quant-feedback-default", max_retries=2),
    )


@dataclass
class QuantConfig:
    workspace_root: str = "/tmp/rd_agent_workspace/quant"
    n_stocks: int = 50
    n_days: int = 500
    data_seed: int = 42
    backtest_config: dict[str, Any] = field(default_factory=dict)
    default_step_overrides: StepOverrideConfig = field(default_factory=default_quant_step_overrides)
    data_provider: QuantDataProvider | None = None


class QuantScenarioPlugin(ScenarioPlugin):
    def build_context(self, run_session: RunSession, input_payload: dict[str, Any]) -> ScenarioContext:
        return ScenarioContext(
            run_id=run_session.run_id,
            scenario_name=run_session.scenario,
            input_payload=dict(input_payload),
            task_summary=str(input_payload.get("task_summary", "mine alpha factors")),
            step_config=StepOverrideConfig.from_dict(input_payload.get("step_config")),
        )


class QuantProposalEngine(ProposalEngine):
    def __init__(self, llm_adapter: LLMAdapter) -> None:
        self._llm = llm_adapter

    def propose(
        self,
        task_summary: str,
        context: ContextPack,
        parent_ids: list[str],
        plan: Plan,
        scenario: ScenarioContext,
    ) -> Proposal:
        _ = context
        _ = parent_ids
        _ = plan
        iteration = int(scenario.input_payload.get("loop_index", 0))
        previous_results = scenario.input_payload.get("previous_results", [])

        prompt = (
            FACTOR_PROPOSAL_SYSTEM_PROMPT
            + "\n\n"
            + FACTOR_PROPOSAL_USER_TEMPLATE.format(
                task_summary=task_summary or scenario.task_summary,
                previous_factors="\n".join(str(r) for r in previous_results) or "None yet",
                feedback="No feedback yet." if not previous_results else "See previous results above.",
            )
        )
        draft = self._llm.generate_structured(
            prompt,
            ProposalDraft,
            model_config=scenario.step_config.proposal,
        )
        return Proposal(
            proposal_id=f"quant-proposal-{iteration}",
            summary=draft.summary,
            constraints=draft.constraints,
            virtual_score=draft.virtual_score,
        )


class QuantExperimentGenerator(ExperimentGenerator):
    def __init__(self, workspace_root: str) -> None:
        self._workspace_root = Path(workspace_root)

    def generate(
        self,
        proposal: Proposal,
        run_session: RunSession,
        loop_state: LoopState,
        parent_ids: list[str],
    ) -> ExperimentNode:
        branch_id = run_session.active_branch_ids[0] if run_session.active_branch_ids else "main"
        parent_node_id: str | None = parent_ids[0] if parent_ids else None
        node_id = f"quant-node-{run_session.run_id}-{branch_id}-{loop_state.iteration}"
        workspace_ref = self._workspace_root / run_session.run_id / node_id
        return ExperimentNode(
            node_id=node_id,
            run_id=run_session.run_id,
            branch_id=branch_id,
            parent_node_id=parent_node_id,
            loop_index=loop_state.iteration,
            step_state=StepState.EXPERIMENT_READY,
            hypothesis={"text": proposal.summary, "component": "QuantFactor"},
            workspace_ref=str(workspace_ref),
            result_ref=str(workspace_ref / "result"),
            feedback_ref="",
        )


class QuantCoder(Coder):
    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        self._llm = llm_adapter

    def develop(
        self,
        experiment: ExperimentNode,
        proposal: Proposal,
        scenario: ScenarioContext,
    ) -> CodeArtifact:
        workspace = Path(experiment.workspace_ref)
        workspace.mkdir(parents=True, exist_ok=True)

        factor_code = self._generate_factor_code(proposal, scenario)
        (workspace / "factor.py").write_text(factor_code, encoding="utf-8")
        (workspace / "proposal.txt").write_text(proposal.summary, encoding="utf-8")

        return CodeArtifact(
            artifact_id=f"quant-artifact-{experiment.node_id}",
            description=proposal.summary,
            location=str(workspace),
        )

    def _generate_factor_code(self, proposal: Proposal, scenario: ScenarioContext) -> str:
        if self._llm is None:
            return _DEFAULT_FACTOR_CODE

        prompt = (
            FACTOR_CODE_SYSTEM_PROMPT
            + "\n\n"
            + FACTOR_CODE_USER_TEMPLATE.format(
                factor_hypothesis=proposal.summary,
                data_schema=DATA_SCHEMA_DESCRIPTION,
            )
        )
        from llm import CodeDraft

        try:
            draft, code = self._llm.generate_code(
                prompt,
                CodeDraft,
                model_config=scenario.step_config.coding,
            )
            if code and "def compute_factor" in code:
                return code
            # Fallback: check if code ended up in description field
            desc = getattr(draft, "description", "") or ""
            if "def compute_factor" in desc:
                return desc
        except Exception:
            pass
        return _DEFAULT_FACTOR_CODE


_DEFAULT_FACTOR_CODE = """\
import pandas as pd

def compute_factor(df):
    return df.groupby('stock_id')['close'].pct_change(20).fillna(0)
"""


class QuantRunner(Runner):
    def __init__(self, config: QuantConfig | None = None) -> None:
        self._config = config or QuantConfig()

    def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult:
        workspace = Path(artifact.location)
        factor_path = workspace / "factor.py"

        if not factor_path.exists():
            return ExecutionResult(
                run_id=scenario.run_id,
                exit_code=1,
                logs_ref="factor.py not found in workspace",
                artifacts_ref=json.dumps([]),
                duration_sec=0.0,
                timed_out=False,
            )

        factor_code = factor_path.read_text(encoding="utf-8")
        if self._config.data_provider is None:
            raise RuntimeError(
                "QuantConfig.data_provider is required. "
                "Use YFinanceDataProvider for real data or MockDataProvider for tests. "
                "Example: QuantConfig(data_provider=YFinanceDataProvider("
                "tickers=[...], start='2023-01-01', end='2024-12-31'))"
            )
        ohlcv = self._config.data_provider.load()
        backtester = LightweightBacktester(config=self._config.backtest_config or None)
        bt_result = backtester.run(ohlcv, factor_code)

        result_path = workspace / "result.json"
        result_path.write_text(json.dumps(bt_result, default=_json_safe), encoding="utf-8")

        if bt_result["status"] == "error":
            return ExecutionResult(
                run_id=scenario.run_id,
                exit_code=1,
                logs_ref=bt_result.get("error", "unknown error"),
                artifacts_ref=json.dumps([str(result_path)]),
                duration_sec=0.0,
                timed_out=False,
            )

        metrics = bt_result.get("metrics", {})
        logs = json.dumps(
            {
                "status": "success",
                **{k: v for k, v in metrics.items() if isinstance(v, (int, float, str))},
            }
        )

        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=0,
            logs_ref=logs,
            artifacts_ref=json.dumps([str(result_path)]),
            duration_sec=0.0,
            timed_out=False,
        )


def _json_safe(obj: Any) -> Any:
    import numpy as np
    import pandas as pd

    if isinstance(obj, pd.Series):
        return obj.tolist()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return str(obj)


class QuantFeedbackAnalyzer(FeedbackAnalyzer):
    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        self._llm = llm_adapter

    def summarize(
        self,
        experiment: ExperimentNode,
        result: ExecutionResult,
        score: Score | None = None,
    ) -> FeedbackRecord:
        usefulness_eligible = result.resolve_outcome().usefulness_eligible

        if self._llm is None:
            try:
                logs_data = json.loads(result.logs_ref or "{}")
            except (json.JSONDecodeError, TypeError):
                logs_data = {}
            succeeded = logs_data.get("status") == "success"
            sharpe = float(logs_data.get("sharpe", 0.0) or 0.0)
            return FeedbackRecord(
                feedback_id=f"quant-fb-{experiment.node_id}",
                decision=succeeded and usefulness_eligible,
                acceptable=succeeded and usefulness_eligible,
                reason=f"sharpe={sharpe:.4f}" if succeeded else "backtest failed",
                observations=result.logs_ref[:200] if result.logs_ref else "",
                code_change_summary="",
            )

        hypothesis_text = (
            experiment.hypothesis.get("text", "")
            if isinstance(experiment.hypothesis, dict)
            else str(experiment.hypothesis)
        )
        try:
            logs_data = json.loads(result.logs_ref or "{}")
        except (json.JSONDecodeError, TypeError):
            logs_data = {}
        prompt = FEEDBACK_ANALYSIS_TEMPLATE.format(
            factor_code=hypothesis_text,
            sharpe=float(logs_data.get("sharpe", 0.0) or 0.0),
            ic=float(logs_data.get("ic_mean", 0.0) or 0.0),
            icir=float(logs_data.get("icir", 0.0) or 0.0),
            mdd=float(logs_data.get("mdd", 0.0) or 0.0),
            execution_logs=result.logs_ref[:500] if result.logs_ref else "",
        )
        from llm import FeedbackDraft as _FeedbackDraft

        try:
            draft = self._llm.generate_structured(prompt, _FeedbackDraft, model_config=None)
            return FeedbackRecord(
                feedback_id=f"quant-fb-{experiment.node_id}",
                decision=draft.decision and usefulness_eligible,
                acceptable=draft.acceptable and usefulness_eligible,
                reason=draft.reason,
                observations=draft.observations,
                code_change_summary=draft.code_change_summary,
            )
        except Exception:
            return FeedbackRecord(
                feedback_id=f"quant-fb-{experiment.node_id}",
                decision=False,
                acceptable=False,
                reason="feedback generation failed",
                observations=result.logs_ref[:200] if result.logs_ref else "",
                code_change_summary="",
            )


def _validate_quant_usefulness(gate_input: UsefulnessGateInput) -> str | None:
    payload = gate_input.structured_payload
    if not isinstance(payload, dict):
        return "missing structured payload"
    if payload.get("status") != "success":
        return f"backtest failed: {payload.get('status', 'unknown')}"

    sharpe = payload.get("sharpe")
    if sharpe is None or (isinstance(sharpe, float) and math.isnan(sharpe)):
        return "sharpe ratio missing or NaN"
    if isinstance(sharpe, (int, float)) and sharpe < METRIC_THRESHOLDS["sharpe"]:
        return f"sharpe {sharpe:.3f} below threshold {METRIC_THRESHOLDS['sharpe']}"

    ic = payload.get("ic_mean")
    if ic is not None and isinstance(ic, (int, float)) and not math.isnan(ic) and ic < METRIC_THRESHOLDS["ic"]:
        return f"IC {ic:.4f} below threshold {METRIC_THRESHOLDS['ic']}"

    return None


def build_quant_bundle(
    config: QuantConfig | None = None,
    llm_adapter: LLMAdapter | None = None,
) -> PluginBundle:
    plugin_config = config or QuantConfig()
    if llm_adapter is None:
        raise RuntimeError(
            "llm_adapter is required for build_quant_bundle(). "
            "Configure a real LLM provider, e.g.: "
            "LLMAdapter(provider=LiteLLMProvider("
            "api_key=os.environ['GEMINI_API_KEY'], model='gemini/gemini-2.5-flash'"
            "), config=LLMAdapterConfig(max_retries=2))"
        )
    adapter = llm_adapter

    return PluginBundle(
        scenario_name="quant",
        scenario_plugin=QuantScenarioPlugin(),
        proposal_engine=QuantProposalEngine(adapter),
        experiment_generator=QuantExperimentGenerator(workspace_root=plugin_config.workspace_root),
        coder=QuantCoder(adapter),
        runner=QuantRunner(config=plugin_config),
        feedback_analyzer=QuantFeedbackAnalyzer(adapter),
        scene_usefulness_validator=_validate_quant_usefulness,
        default_step_overrides=plugin_config.default_step_overrides,
    )


def quant_manifest(config: QuantConfig | None = None) -> ScenarioManifest:
    plugin_config = config or QuantConfig()
    return ScenarioManifest(
        scenario_name="quant",
        title="Quant Factor Mining",
        description="Automated alpha factor mining loop: LLM proposes factors, backtest evaluates, feedback improves.",
        tags=["built-in", "quant", "factor-mining"],
        supports_branching=True,
        supports_resume=True,
        supports_local_execution=True,
        default_step_overrides=plugin_config.default_step_overrides,
    )
