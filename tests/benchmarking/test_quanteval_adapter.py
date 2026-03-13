from __future__ import annotations

import unittest

from benchmarking.adapters.quanteval_adapter import QuantEvalAdapter
from benchmarking.result_schema import FailureBucket
from benchmarking.adapters.quanteval_adapter import QuantEvalAdapterError


class QuantEvalAdapterTests(unittest.TestCase):
    def test_maps_backtest_metrics_into_benchmark_case_result(self) -> None:
        adapter = QuantEvalAdapter()
        result = adapter.evaluate_case(
            task_id="quant-case-1",
            profile="smoke",
            runtime_status="COMPLETED",
            runtime_metadata={
                "llm_provider": "litellm",
                "llm_model": "gpt-4.1-mini",
                "judge_model": None,
            },
            backtest_result={
                "status": "SUCCESS",
                "score": 0.72,
                "metrics": {
                    "sharpe": 1.4,
                    "max_drawdown": -0.12,
                    "total_return": 0.31,
                },
                "artifacts": {"equity_curve": "artifacts/equity.csv"},
            },
        )

        self.assertEqual(result.scenario, "quant")
        self.assertEqual(result.task_id, "quant-case-1")
        self.assertEqual(result.failure_bucket, FailureBucket.SUCCESS)
        self.assertEqual(result.agent_status, "COMPLETED")
        self.assertEqual(result.scenario_score, 0.72)
        self.assertEqual(result.scenario_metrics["sharpe"], 1.4)
        self.assertEqual(result.scenario_metrics["drawdown"], -0.12)
        self.assertEqual(result.scenario_metrics["returns"], 0.31)
        self.assertEqual(result.scenario_metrics["evaluation_status"], "SUCCESS")

    def test_classifies_invalid_strategy_failures_clearly(self) -> None:
        adapter = QuantEvalAdapter()
        result = adapter.evaluate_case(
            task_id="quant-invalid",
            profile="smoke",
            runtime_status="FAILED",
            runtime_metadata={
                "llm_provider": "litellm",
                "llm_model": "gpt-4.1-mini",
                "judge_model": None,
            },
            backtest_result={
                "status": "INVALID_STRATEGY",
                "error": "signal column missing",
            },
        )

        self.assertEqual(result.failure_bucket, FailureBucket.SCENARIO_EVAL_FAILURE)
        self.assertEqual(result.agent_status, "FAILED")
        self.assertEqual(result.scenario_metrics["error"], "signal column missing")

    def test_raises_clear_error_for_missing_backtest_payload(self) -> None:
        adapter = QuantEvalAdapter()
        with self.assertRaisesRegex(QuantEvalAdapterError, "missing QuantEval backtest result"):
            adapter.evaluate_case(
                task_id="quant-missing",
                profile="smoke",
                runtime_status="FAILED",
                runtime_metadata={
                    "llm_provider": "litellm",
                    "llm_model": "gpt-4.1-mini",
                    "judge_model": None,
                },
                backtest_result=None,
            )

    def test_raises_clear_error_for_success_without_score(self) -> None:
        adapter = QuantEvalAdapter()
        with self.assertRaisesRegex(QuantEvalAdapterError, "missing QuantEval score"):
            adapter.evaluate_case(
                task_id="quant-missing-score",
                profile="smoke",
                runtime_status="COMPLETED",
                runtime_metadata={
                    "llm_provider": "litellm",
                    "llm_model": "gpt-4.1-mini",
                    "judge_model": None,
                },
                backtest_result={
                    "status": "SUCCESS",
                    "metrics": {"sharpe": 1.0},
                },
            )


if __name__ == "__main__":
    unittest.main()
