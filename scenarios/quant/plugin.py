"""Quant scenario plugin: factor mining loop via LLM + lightweight backtester."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

import pandas as pd

from data_models import (
    CodeArtifact,
    ContextPack,
    DataSplitManifest,
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
from evaluation_service.stratified_splitter import StratifiedSplitter

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
    def build_context(self, run_session: RunSession, input_payload: Dict[str, Any]) -> ScenarioContext:
        split_manifest = _build_quant_split_manifest(input_payload)
        return ScenarioContext(
            run_id=run_session.run_id,
            scenario_name=run_session.scenario,
            input_payload=dict(input_payload),
            config={"split_manifest": split_manifest},
            task_summary=str(input_payload.get("task_summary", "mine alpha factors")),
            step_config=StepOverrideConfig.from_dict(input_payload.get("step_config")),
        )


def _build_quant_split_manifest(input_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data_ids = _normalize_quant_ids(input_payload.get("data_ids"))
    labels = _normalize_quant_labels(input_payload.get("labels"))
    ordered_pairs = _extract_quant_ordered_pairs(input_payload)

    if not data_ids and ordered_pairs:
        data_ids = [data_id for _, data_id in ordered_pairs]

    if not data_ids:
        return None

    splitter = StratifiedSplitter(
        train_ratio=_resolve_quant_ratio(input_payload.get("train_ratio"), 0.9),
        test_ratio=_resolve_quant_ratio(input_payload.get("test_ratio"), 0.1),
        seed=_resolve_quant_seed(input_payload.get("split_seed", input_payload.get("seed", 42))),
    )
    if labels is not None and len(labels) == len(data_ids):
        return asdict(splitter.split(data_ids, labels=labels))
    if ordered_pairs:
        ordered_ids = [data_id for _, data_id in ordered_pairs]
        return asdict(_build_ordered_manifest(ordered_ids, splitter))
    return asdict(splitter.split(data_ids, labels=None))


def _extract_quant_ordered_pairs(input_payload: Dict[str, Any]) -> List[tuple[str, str]]:
    direct_data_ids = _normalize_quant_ids(input_payload.get("data_ids"))
    order_values = input_payload.get("timestamps")
    if not isinstance(order_values, list):
        order_values = input_payload.get("dates")
    if isinstance(order_values, list) and len(order_values) == len(direct_data_ids):
        return sorted(
            [
                (str(order_value), data_id)
                for order_value, data_id in zip(order_values, direct_data_ids)
                if str(data_id).strip()
            ],
            key=lambda item: item[0],
        )

    frame = _coerce_quant_frame(input_payload)
    if frame is None or frame.empty:
        return []

    normalized = frame.copy()
    id_column = _first_quant_column(normalized, ["id", "data_id", "row_id"])
    if not id_column:
        date_column = _first_quant_column(normalized, ["date", "datetime", "timestamp"])
        stock_column = _first_quant_column(normalized, ["stock_id", "symbol", "ticker", "asset_id"])
        if date_column and stock_column:
            normalized["__split_id__"] = normalized[date_column].astype(str) + "|" + normalized[stock_column].astype(str)
            id_column = "__split_id__"
        elif date_column:
            normalized["__split_id__"] = normalized[date_column].astype(str)
            id_column = "__split_id__"
        else:
            normalized["__split_id__"] = normalized.index.astype(str)
            id_column = "__split_id__"

    order_column = _first_quant_column(normalized, ["date", "datetime", "timestamp"]) or id_column
    normalized = normalized.sort_values(by=[order_column, id_column], kind="stable")
    return [
        (str(row[order_column]), str(row[id_column]))
        for _, row in normalized.iterrows()
    ]


def _coerce_quant_frame(input_payload: Dict[str, Any]) -> Optional[pd.DataFrame]:
    for key in ("ohlcv", "data_frame", "data", "records"):
        value = input_payload.get(key)
        if isinstance(value, pd.DataFrame):
            return value
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            return pd.DataFrame(value)
    return None


def _build_ordered_manifest(data_ids: List[str], splitter: StratifiedSplitter) -> DataSplitManifest:
    if not data_ids:
        return DataSplitManifest(seed=splitter._seed)

    n = len(data_ids)
    n_test = max(1, round(n * splitter._test_ratio)) if n > 1 else 0
    n_train = n - n_test
    return DataSplitManifest(
        train_ids=list(data_ids[:n_train]),
        val_ids=[],
        test_ids=list(data_ids[n_train:]),
        seed=splitter._seed,
    )


def _first_quant_column(frame: pd.DataFrame, candidates: List[str]) -> str:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return ""


def _normalize_quant_ids(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalize_quant_labels(value: Any) -> Optional[List[str]]:
    if not isinstance(value, list):
        return None
    labels = [str(item) for item in value]
    return labels if labels else None


def _resolve_quant_ratio(value: Any, default: float) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return default
    return resolved if resolved > 0 else default


def _resolve_quant_seed(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 42


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
        iteration = int(scenario.input_payload.get("loop_index", 0))
        previous_results = scenario.input_payload.get("previous_results", [])
        summary = task_summary or scenario.task_summary or "mine alpha factors"

        highlights = list(getattr(context, "highlights", None) or [])
        scored_items = list(getattr(context, "scored_items", None) or [])
        context_lines: List[str] = [f"- {item}" for item in highlights if str(item).strip()]
        for item, score in scored_items[:3]:
            item_text = str(item).strip()
            if not item_text:
                continue
            try:
                score_text = f"{float(score):.3f}"
            except (TypeError, ValueError):
                score_text = "N/A"
            context_lines.append(f"- {item_text} (score={score_text})")
        if not context_lines:
            context_lines = ["- None"]

        guidance_items = list(getattr(plan, "guidance", None) or []) if plan is not None else []
        guidance_text = (
            "\n".join(f"- {str(item).strip()}" for item in guidance_items if str(item).strip())
            or "No specific guidance"
        )
        parent_text = ", ".join(parent_ids) if parent_ids else "None"
        context_text = "\n".join(context_lines)
        enriched_context_block = (
            "\n\nPrior Context:\n"
            f"{context_text}\n\n"
            "Strategic Guidance:\n"
            f"{guidance_text}\n\n"
            "Parent Branch Continuity:\n"
            f"{parent_text}"
        )

        prompt = (
            FACTOR_PROPOSAL_SYSTEM_PROMPT
            + "\n\n"
            + FACTOR_PROPOSAL_USER_TEMPLATE.format(
                task_summary=summary,
                previous_factors="\n".join(str(r) for r in previous_results) or "None yet",
                feedback="No feedback yet." if not previous_results else "See previous results above.",
            )
            + enriched_context_block
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

        factor_code = self._generate_factor_code(proposal, scenario, experiment)
        (workspace / "factor.py").write_text(factor_code, encoding="utf-8")
        (workspace / "proposal.txt").write_text(proposal.summary, encoding="utf-8")

        return CodeArtifact(
            artifact_id=f"quant-artifact-{experiment.node_id}",
            description=proposal.summary,
            location=str(workspace),
        )

    def _enrich_hypothesis_with_feedback(self, hypothesis: str, experiment: ExperimentNode) -> str:
        feedback_text = None
        if isinstance(experiment.hypothesis, dict):
            feedback_text = experiment.hypothesis.get("_costeer_feedback")
        
        if feedback_text and isinstance(feedback_text, str) and feedback_text.strip():
            return f"{hypothesis}\n\nPrevious round feedback:\n{feedback_text}"
        return hypothesis

    def _generate_factor_code(self, proposal: Proposal, scenario: ScenarioContext, experiment: ExperimentNode) -> str:
        if self._llm is None:
            return _DEFAULT_FACTOR_CODE

        factor_hypothesis = self._enrich_hypothesis_with_feedback(proposal.summary, experiment)
        prompt = (
            FACTOR_CODE_SYSTEM_PROMPT
            + "\n\n"
            + FACTOR_CODE_USER_TEMPLATE.format(
                factor_hypothesis=factor_hypothesis,
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
        logger = logging.getLogger(__name__)
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
        ohlcv: pd.DataFrame = self._config.data_provider.load()
        debug_config = scenario.config.get("debug_config")
        if (
            debug_config
            and getattr(debug_config, "debug_mode", False)
            and getattr(debug_config, "supports_debug_sampling", False)
        ):
            sample_fraction = float(getattr(debug_config, "sample_fraction", 0.1))
            sample_fraction = max(0.0, min(sample_fraction, 1.0))
            
            if sample_fraction == 0.0:
                logger.warning(
                    "Debug mode: sample_fraction=0 detected; using full dataset (minimum 1 date, 1 stock)"
                )
            
            logger.info("Debug mode active: sampling %.0f%% of data", sample_fraction * 100)
            if not ohlcv.empty:
                dates = sorted(ohlcv["date"].unique())
                stocks = sorted(ohlcv["stock_id"].unique())
                keep_dates = dates[: max(1, int(len(dates) * sample_fraction))]
                keep_stocks = stocks[: max(1, int(len(stocks) * sample_fraction))]
                ohlcv = cast(
                    pd.DataFrame,
                    ohlcv[
                        ohlcv["date"].isin(keep_dates) & ohlcv["stock_id"].isin(keep_stocks)
                    ].copy(),
                )
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
