"""Tests for quant scenario constants (TDD: RED -> GREEN -> REFACTOR)."""

import pytest
from scenarios.quant.constants import (
    BACKTEST_CONFIG,
    BLOCKED_IMPORTS,
    CONSTRAINT_METRICS,
    MAX_FACTOR_COMPUTE_SEC,
    MAX_FACTOR_MEMORY_MB,
    METRIC_THRESHOLDS,
    PRIMARY_METRIC,
    SAFE_IMPORTS,
)


class TestMetricThresholds:
    def test_metric_thresholds_exist(self):
        expected_keys = {"sharpe", "ic", "icir", "rank_ic", "rank_icir", "arr", "mdd", "calmar"}
        assert set(METRIC_THRESHOLDS.keys()) == expected_keys

    def test_threshold_ranges_valid(self):
        assert METRIC_THRESHOLDS["sharpe"] > 0
        assert 0 < METRIC_THRESHOLDS["ic"] < 1
        assert -1 < METRIC_THRESHOLDS["mdd"] < 0, "MDD threshold must be negative"
        assert METRIC_THRESHOLDS["calmar"] > 0
        assert METRIC_THRESHOLDS["arr"] > 0

    def test_primary_metric_is_sharpe(self):
        assert PRIMARY_METRIC == "sharpe"
        assert PRIMARY_METRIC in METRIC_THRESHOLDS

    def test_constraint_metrics_subset_of_thresholds(self):
        for m in CONSTRAINT_METRICS:
            assert m in METRIC_THRESHOLDS, f"{m} not in METRIC_THRESHOLDS"


class TestBacktestConfig:
    def test_default_backtest_config(self):
        required_keys = {"rebalance_freq", "train_end", "test_start", "initial_capital", "commission_rate"}
        for key in required_keys:
            assert key in BACKTEST_CONFIG, f"Missing key: {key}"

    def test_train_test_split_order(self):
        from datetime import date
        train_end = date.fromisoformat(BACKTEST_CONFIG["train_end"])
        test_start = date.fromisoformat(BACKTEST_CONFIG["test_start"])
        assert test_start > train_end, "test_start must be after train_end"

    def test_initial_capital_positive(self):
        assert BACKTEST_CONFIG["initial_capital"] > 0

    def test_rates_in_valid_range(self):
        assert 0 < BACKTEST_CONFIG["commission_rate"] < 0.1
        assert 0 < BACKTEST_CONFIG["slippage_rate"] < 0.1


class TestImportSafety:
    def test_import_whitelist_contains_numpy_pandas(self):
        assert "numpy" in SAFE_IMPORTS
        assert "pandas" in SAFE_IMPORTS

    def test_import_blacklist_contains_dangerous_modules(self):
        assert "os" in BLOCKED_IMPORTS
        assert "subprocess" in BLOCKED_IMPORTS
        assert "requests" in BLOCKED_IMPORTS

    def test_no_overlap_between_safe_and_blocked(self):
        overlap = SAFE_IMPORTS & BLOCKED_IMPORTS
        assert len(overlap) == 0, f"Overlap found: {overlap}"


class TestResourceLimits:
    def test_max_compute_sec_positive(self):
        assert MAX_FACTOR_COMPUTE_SEC > 0

    def test_max_memory_mb_positive(self):
        assert MAX_FACTOR_MEMORY_MB > 0
