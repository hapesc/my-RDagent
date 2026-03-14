"""QuantEval adapter for mapping CTA-style backtest results into benchmark results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from benchmarking.result_schema import BenchmarkCaseResult, FailureBucket


class QuantEvalAdapterError(ValueError):
    """Raised when a QuantEval payload cannot be mapped."""


@dataclass
class QuantEvalAdapter:
    def evaluate_case(
        self,
        *,
        task_id: str,
        profile: str,
        runtime_metadata: dict[str, Any],
        backtest_result: dict[str, Any] | None,
        runtime_status: str | None = None,
    ) -> BenchmarkCaseResult:
        if backtest_result is None:
            raise QuantEvalAdapterError("missing QuantEval backtest result")

        status = str(backtest_result.get("status", "UNKNOWN"))
        metrics = dict(backtest_result.get("metrics", {}))
        artifacts = dict(backtest_result.get("artifacts", {}))

        failure_bucket = FailureBucket.SUCCESS
        scenario_score = backtest_result.get("score")
        if status == "INVALID_STRATEGY":
            failure_bucket = FailureBucket.SCENARIO_EVAL_FAILURE
            scenario_score = None
        elif status not in {"SUCCESS", "COMPLETED"}:
            failure_bucket = FailureBucket.SCENARIO_EVAL_FAILURE
        elif scenario_score is None:
            raise QuantEvalAdapterError("missing QuantEval score for successful backtest result")

        scenario_metrics = {
            "sharpe": metrics.get("sharpe"),
            "drawdown": metrics.get("max_drawdown"),
            "returns": metrics.get("total_return"),
        }
        if "error" in backtest_result:
            scenario_metrics["error"] = backtest_result["error"]

        return BenchmarkCaseResult(
            scenario="quant",
            task_id=task_id,
            profile=profile,
            agent_status=str(runtime_status or runtime_metadata.get("agent_status") or "UNKNOWN"),
            llm_provider=str(runtime_metadata.get("llm_provider", "")),
            llm_model=str(runtime_metadata.get("llm_model", "")),
            judge_model=runtime_metadata.get("judge_model"),
            failure_bucket=failure_bucket,
            scenario_score=scenario_score,
            scenario_metrics={"evaluation_status": status, **scenario_metrics},
            artifact_refs=artifacts,
        )
