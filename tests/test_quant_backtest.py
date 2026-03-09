"""Tests for LightweightBacktester (TDD)."""

import numpy as np
import pandas as pd
import pytest

from scenarios.quant.backtest import LightweightBacktester
from scenarios.quant.mock_data import generate_ohlcv

_SIMPLE_FACTOR_CODE = """
import numpy as np
import pandas as pd

def compute_factor(df):
    return df.groupby('stock_id')['close'].pct_change(5).fillna(0)
"""

_CONSTANT_FACTOR_CODE = """
import pandas as pd

def compute_factor(df):
    return pd.Series(1.0, index=df.index)
"""

_BAD_SAFETY_CODE = "import os\ndef compute_factor(df): return df['close']"

_SYNTAX_ERROR_CODE = "def compute_factor(df\n    return df['close']"

_MISSING_FUNCTION_CODE = """
import pandas as pd
result = 42
"""

_WRONG_RETURN_TYPE_CODE = """
def compute_factor(df):
    return 42
"""


@pytest.fixture(scope="module")
def small_ohlcv():
    return generate_ohlcv(n_stocks=20, n_days=300, start_date="2020-01-01", seed=0)


_SMALL_BT_CONFIG = {"train_end": "2020-09-30", "test_start": "2020-10-01"}


class TestBacktesterInit:
    def test_default_config(self):
        bt = LightweightBacktester()
        assert bt.config["top_k"] == 10
        assert bt.config["commission_rate"] == 0.001

    def test_custom_config_merges(self):
        bt = LightweightBacktester(config={"top_k": 5})
        assert bt.config["top_k"] == 5
        assert bt.config["commission_rate"] == 0.001


class TestBacktesterSuccessPath:
    def test_run_returns_success_status(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _SIMPLE_FACTOR_CODE)
        assert result["status"] == "success", result.get("error", "")

    def test_metrics_keys_present(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _SIMPLE_FACTOR_CODE)
        assert result["status"] == "success"
        required = {"ic_mean", "icir", "rank_ic_mean", "rank_icir", "sharpe", "mdd", "arr", "calmar"}
        for key in required:
            assert key in result["metrics"], f"Missing metric: {key}"

    def test_portfolio_returns_is_series(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _SIMPLE_FACTOR_CODE)
        assert isinstance(result["portfolio_returns"], pd.Series)
        assert len(result["portfolio_returns"]) > 0

    def test_constant_factor_runs_without_error(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _CONSTANT_FACTOR_CODE)
        assert result["status"] == "success"

    def test_train_test_split_fields_present(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _SIMPLE_FACTOR_CODE)
        assert "train_end" in result
        assert "test_start" in result

    def test_custom_top_k(self, small_ohlcv):
        bt = LightweightBacktester(config={**_SMALL_BT_CONFIG, "top_k": 3})
        result = bt.run(small_ohlcv, _SIMPLE_FACTOR_CODE)
        assert result["status"] == "success"


class TestBacktesterErrorPath:
    def test_safety_violation_returns_error(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _BAD_SAFETY_CODE)
        assert result["status"] == "error"
        assert "safety" in result["error"].lower()

    def test_syntax_error_returns_error(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _SYNTAX_ERROR_CODE)
        assert result["status"] == "error"

    def test_missing_compute_factor_returns_error(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _MISSING_FUNCTION_CODE)
        assert result["status"] == "error"
        assert "compute_factor" in result["error"]

    def test_wrong_return_type_returns_error(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _WRONG_RETURN_TYPE_CODE)
        assert result["status"] == "error"

    def test_missing_column_returns_error(self):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        bad_df = pd.DataFrame({"date": ["2020-01-01"], "open": [100.0]})
        result = bt.run(bad_df, _SIMPLE_FACTOR_CODE)
        assert result["status"] == "error"


class TestBacktesterMetricsRange:
    def test_mdd_is_negative_or_nan(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _SIMPLE_FACTOR_CODE)
        mdd = result["metrics"]["mdd"]
        assert np.isnan(mdd) or mdd <= 0

    def test_sharpe_is_finite_or_nan(self, small_ohlcv):
        bt = LightweightBacktester(config=_SMALL_BT_CONFIG)
        result = bt.run(small_ohlcv, _SIMPLE_FACTOR_CODE)
        sharpe = result["metrics"]["sharpe"]
        assert np.isnan(sharpe) or np.isfinite(sharpe)
