"""Tests for quant metrics computation (TDD)."""

import math

import numpy as np
import pandas as pd

from scenarios.quant.metrics import (
    compute_all_metrics,
    compute_arr,
    compute_calmar,
    compute_ic,
    compute_icir,
    compute_mdd,
    compute_rank_ic,
    compute_rank_icir,
    compute_sharpe,
)


def _dates(n: int) -> pd.Series:
    return pd.Series(pd.date_range("2020-01-01", periods=n, freq="B"))


class TestComputeIC:
    def test_ic_perfect_correlation(self):
        # IC is cross-sectional (per date across stocks): need multiple stocks per date
        n_dates = 20
        n_stocks = 10
        dates_list = []
        factor_list = []
        actual_list = []
        for d in pd.date_range("2020-01-01", periods=n_dates, freq="B"):
            ranks = np.arange(float(n_stocks))
            dates_list.extend([d] * n_stocks)
            factor_list.extend(ranks.tolist())
            actual_list.extend(ranks.tolist())  # perfect rank match
        result = compute_ic(pd.Series(factor_list), pd.Series(actual_list), pd.Series(dates_list))
        assert abs(result["ic_mean"] - 1.0) < 1e-6

    def test_ic_negative_correlation(self):
        n_dates = 20
        n_stocks = 10
        dates_list = []
        factor_list = []
        actual_list = []
        for d in pd.date_range("2020-01-01", periods=n_dates, freq="B"):
            ranks = np.arange(float(n_stocks))
            dates_list.extend([d] * n_stocks)
            factor_list.extend(ranks.tolist())
            actual_list.extend((-ranks).tolist())
        result = compute_ic(pd.Series(factor_list), pd.Series(actual_list), pd.Series(dates_list))
        assert abs(result["ic_mean"] + 1.0) < 1e-6

    def test_ic_all_nan_factor(self):
        n = 20
        dates = _dates(n)
        factor = pd.Series([float("nan")] * n)
        actual = pd.Series(np.random.randn(n))
        result = compute_ic(factor, actual, dates)
        assert math.isnan(result["ic_mean"])

    def test_ic_constant_factor(self):
        n = 20
        dates = _dates(n)
        factor = pd.Series([1.0] * n)
        actual = pd.Series(np.random.randn(n))
        result = compute_ic(factor, actual, dates)
        assert math.isnan(result["ic_mean"])

    def test_ic_returns_series(self):
        n = 50
        dates = _dates(n)
        factor = pd.Series(np.random.randn(n))
        actual = pd.Series(np.random.randn(n))
        result = compute_ic(factor, actual, dates)
        assert "ic_series" in result
        assert isinstance(result["ic_series"], pd.Series)


class TestComputeICIR:
    def test_icir_stable_ic(self):
        ic_series = pd.Series([0.05] * 100)
        icir = compute_icir(ic_series)
        assert math.isnan(icir) or icir > 10

    def test_icir_zero_std(self):
        ic_series = pd.Series([0.03] * 50)
        icir = compute_icir(ic_series)
        assert math.isnan(icir)

    def test_icir_formula(self):
        ic_series = pd.Series([0.02, 0.04, 0.06, 0.08])
        expected = ic_series.mean() / ic_series.std()
        result = compute_icir(ic_series)
        assert abs(result - expected) < 1e-6


class TestRankIC:
    def test_rank_ic_perfect(self):
        # RankIC is also cross-sectional, needs multiple stocks per date
        n_dates = 20
        n_stocks = 10
        dates_list = []
        factor_list = []
        actual_list = []
        for d in pd.date_range("2020-01-01", periods=n_dates, freq="B"):
            ranks = np.arange(float(n_stocks))
            dates_list.extend([d] * n_stocks)
            factor_list.extend(ranks.tolist())
            actual_list.extend(ranks.tolist())
        result = compute_rank_ic(pd.Series(factor_list), pd.Series(actual_list), pd.Series(dates_list))
        assert abs(result["rank_ic_mean"] - 1.0) < 1e-6

    def test_rank_icir_delegation(self):
        rank_ic_series = pd.Series([0.03, 0.05, 0.04, 0.06])
        expected = compute_icir(rank_ic_series)
        result = compute_rank_icir(rank_ic_series)
        assert abs(result - expected) < 1e-10


class TestComputeSharpe:
    def test_sharpe_positive_returns(self):
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0.002, 0.01, 252))  # positive mean, non-zero std
        sharpe = compute_sharpe(returns)
        assert sharpe > 0

    def test_sharpe_zero_excess(self):
        returns = pd.Series([0.0] * 252)
        sharpe = compute_sharpe(returns)
        assert math.isnan(sharpe)

    def test_sharpe_annualization(self):
        daily_mean = 0.001
        daily_std = 0.01
        returns = pd.Series(np.random.default_rng(0).normal(daily_mean, daily_std, 252))
        sharpe = compute_sharpe(returns)
        approx = (returns.mean() / returns.std()) * math.sqrt(252)
        assert abs(sharpe - approx) < 1.0

    def test_sharpe_single_day(self):
        returns = pd.Series([0.01])
        result = compute_sharpe(returns)
        assert math.isnan(result)


class TestComputeMDD:
    def test_mdd_known_drawdown(self):
        prices = pd.Series([100.0, 80.0, 60.0, 70.0])
        returns = prices.pct_change().dropna()
        mdd = compute_mdd(returns)
        assert mdd < 0
        assert mdd <= -0.20

    def test_mdd_monotonic_increase(self):
        returns = pd.Series([0.01] * 100)
        mdd = compute_mdd(returns)
        assert mdd >= -0.001

    def test_mdd_negative_convention(self):
        returns = pd.Series([-0.1, -0.2, 0.0, 0.1])
        mdd = compute_mdd(returns)
        assert mdd < 0


class TestComputeARR:
    def test_arr_known_return(self):
        returns = pd.Series([0.001] * 252)
        arr = compute_arr(returns)
        expected = (1.001) ** 252 - 1
        assert abs(arr - expected) < 0.01

    def test_arr_zero_returns(self):
        returns = pd.Series([0.0] * 252)
        arr = compute_arr(returns)
        assert abs(arr) < 1e-6


class TestComputeCalmar:
    def test_calmar_ratio(self):
        arr = 0.15
        mdd = -0.10
        calmar = compute_calmar(arr, mdd)
        assert abs(calmar - 1.5) < 1e-6

    def test_calmar_nan_propagation(self):
        assert math.isnan(compute_calmar(float("nan"), -0.1))
        assert math.isnan(compute_calmar(0.1, float("nan")))

    def test_calmar_zero_mdd(self):
        assert math.isnan(compute_calmar(0.1, 0.0))


class TestComputeAllMetrics:
    def test_compute_all_metrics_keys(self):
        n = 100
        dates = _dates(n)
        rng = np.random.default_rng(0)
        factor = pd.Series(rng.standard_normal(n))
        actual = pd.Series(rng.standard_normal(n))
        port_returns = pd.Series(rng.normal(0.0002, 0.01, n))
        result = compute_all_metrics(factor, actual, dates, port_returns)
        required_keys = {"ic_mean", "icir", "rank_ic_mean", "rank_icir", "sharpe", "mdd", "arr", "calmar"}
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_compute_all_metrics_no_crash_on_nan(self):
        n = 20
        dates = _dates(n)
        factor = pd.Series([float("nan")] * n)
        actual = pd.Series(np.random.randn(n))
        port_returns = pd.Series([0.0] * n)
        result = compute_all_metrics(factor, actual, dates, port_returns)
        assert isinstance(result, dict)
        assert "ic_mean" in result
