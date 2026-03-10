"""Lightweight pure-Python/NumPy/Pandas backtester for single alpha factors."""

from __future__ import annotations

import traceback
from typing import Any

import pandas as pd

from .code_safety import validate_code_safety
from .constants import BACKTEST_CONFIG
from .metrics import compute_all_metrics


class BacktestError(Exception):
    pass


class LightweightBacktester:
    """Run a single-factor long-only backtest on synthetic OHLCV data.

    The factor_code string must define a callable ``compute_factor(df) -> pd.Series``
    where *df* is the full OHLCV DataFrame and the returned Series has the same
    index as *df*, representing the factor signal for each (date, stock) row.
    """

    def __init__(self, config: dict | None = None) -> None:
        self.config: dict = {**BACKTEST_CONFIG, **(config or {})}

    def run(self, ohlcv_data: pd.DataFrame, factor_code: str) -> dict[str, Any]:
        """Execute backtest pipeline.

        Returns a dict with keys:
            status: "success" | "error"
            error:  str (only when status=="error")
            metrics: dict of computed metrics (only when status=="success")
            portfolio_returns: pd.Series of daily portfolio returns (test period)
            train_end: str
            test_start: str
        """
        safe, reason = validate_code_safety(factor_code)
        if not safe:
            return {"status": "error", "error": f"Code safety violation: {reason}"}

        try:
            factor_values = self._execute_factor(ohlcv_data, factor_code)
        except Exception as exc:
            return {"status": "error", "error": f"Factor execution failed: {exc}\n{traceback.format_exc()}"}

        try:
            result = self._run_backtest(ohlcv_data, factor_values)
        except Exception as exc:
            return {"status": "error", "error": f"Backtest engine failed: {exc}\n{traceback.format_exc()}"}

        return result

    def _execute_factor(self, df: pd.DataFrame, factor_code: str) -> pd.Series:
        namespace: dict = {}
        exec(factor_code, namespace)  # noqa: S102 — code already validated by safety checker
        if "compute_factor" not in namespace:
            raise BacktestError("factor_code must define a function named 'compute_factor(df)'")
        factor_fn = namespace["compute_factor"]
        result = factor_fn(df)
        if isinstance(result, pd.DataFrame):
            if "factor_value" in result.columns:
                merged = df[["date", "stock_id"]].copy()
                merged = merged.merge(result[["date", "stock_id", "factor_value"]], on=["date", "stock_id"], how="left")
                return merged.set_index(["date", "stock_id"])["factor_value"]
            raise BacktestError("compute_factor returned DataFrame but missing 'factor_value' column")
        if not isinstance(result, pd.Series):
            raise BacktestError(f"compute_factor must return pd.Series or pd.DataFrame, got {type(result)}")
        return result

    def _run_backtest(self, ohlcv: pd.DataFrame, factor: pd.Series) -> dict[str, Any]:
        cfg = self.config
        pd.Timestamp(cfg["train_end"])
        test_start = pd.Timestamp(cfg["test_start"])
        top_k: int = cfg["top_k"]
        commission: float = cfg["commission_rate"]
        slippage: float = cfg["slippage_rate"]

        required_cols = {"date", "stock_id", "close"}
        missing = required_cols - set(ohlcv.columns)
        if missing:
            raise BacktestError(f"OHLCV data missing columns: {missing}")

        ohlcv = ohlcv.copy()
        ohlcv["factor"] = factor.values if len(factor) == len(ohlcv) else factor.reindex(ohlcv.index)
        ohlcv["next_return"] = ohlcv.groupby("stock_id")["close"].pct_change().shift(-1)

        test_mask = ohlcv["date"] >= test_start
        test_df = ohlcv[test_mask].dropna(subset=["factor"])

        if test_df.empty:
            raise BacktestError("No test data after applying date split and dropping NaN factors")

        dates_sorted = sorted(test_df["date"].unique())
        daily_returns: list[float] = []
        prev_holdings: set[str] = set()

        for date in dates_sorted:
            day = test_df[test_df["date"] == date].copy()
            day = day.dropna(subset=["factor"])
            if len(day) < max(top_k, 1):
                daily_returns.append(0.0)
                continue

            top_stocks = day.nlargest(top_k, "factor")["stock_id"].tolist()
            current_holdings = set(top_stocks)

            turnover = len(current_holdings.symmetric_difference(prev_holdings)) / max(len(current_holdings), 1)
            transaction_cost = turnover * (commission + slippage)

            stock_returns = day[day["stock_id"].isin(list(current_holdings))]["next_return"].fillna(0.0)
            port_return = float(stock_returns.mean()) - transaction_cost

            daily_returns.append(port_return)
            prev_holdings = current_holdings

        portfolio_returns = pd.Series(daily_returns, index=pd.DatetimeIndex(dates_sorted))

        factor_test = test_df["factor"]
        actual_test = test_df["next_return"].fillna(0.0)
        dates_test = test_df["date"]

        metrics = compute_all_metrics(factor_test, actual_test, dates_test, portfolio_returns)

        return {
            "status": "success",
            "metrics": metrics,
            "portfolio_returns": portfolio_returns,
            "train_end": cfg["train_end"],
            "test_start": cfg["test_start"],
        }
