"""Tests for quantitative mock data generation (TDD: RED → GREEN → REFACTOR)."""

import numpy as np
import pandas as pd

from scenarios.quant.mock_data import generate_ohlcv


class TestGenerateOHLCV:
    """Test suite for generate_ohlcv() function."""

    def test_generate_ohlcv_shape(self):
        """Test output shape: 50 stocks × 500 days = 25000 rows, 7 columns."""
        df = generate_ohlcv(n_stocks=50, n_days=500)

        assert df.shape == (25000, 7), f"Expected shape (25000, 7), got {df.shape}"
        assert list(df.columns) == ["date", "stock_id", "open", "high", "low", "close", "volume"]

    def test_ohlcv_constraints(self):
        """Test OHLC constraints: High ≥ max(Open, Close), Low ≤ min(Open, Close), Volume > 0."""
        df = generate_ohlcv(n_stocks=10, n_days=100)

        # High must be >= max(open, close)
        high_violations = df[df["high"] < df[["open", "close"]].max(axis=1)]
        assert len(high_violations) == 0, f"Found {len(high_violations)} high constraint violations"

        # Low must be <= min(open, close)
        low_violations = df[df["low"] > df[["open", "close"]].min(axis=1)]
        assert len(low_violations) == 0, f"Found {len(low_violations)} low constraint violations"

        # Volume must be > 0
        volume_violations = df[df["volume"] <= 0]
        assert len(volume_violations) == 0, f"Found {len(volume_violations)} volume constraint violations"

    def test_market_correlation_structure(self):
        """Test stocks have pairwise correlation > 0 (not pure random)."""
        df = generate_ohlcv(n_stocks=10, n_days=500, seed=42)

        # Compute daily returns per stock
        pivot_close = df.pivot(index="date", columns="stock_id", values="close")
        returns = pivot_close.pct_change().dropna()

        # Check correlation matrix
        corr_matrix = returns.corr()

        # All pairwise correlations should be positive (>= 0, ideally > 0.1)
        off_diag_corrs = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)]
        assert np.all(off_diag_corrs > 0), f"Expected all correlations > 0, got min={off_diag_corrs.min()}"
        assert np.mean(off_diag_corrs) > 0.1, f"Expected mean correlation > 0.1, got {np.mean(off_diag_corrs)}"

    def test_no_missing_dates(self):
        """Test trading days are weekdays only, no gaps."""
        df = generate_ohlcv(n_stocks=5, n_days=100, start_date="2020-01-01")

        # Get unique dates
        unique_dates = df["date"].unique()
        unique_dates = pd.to_datetime(unique_dates)

        # Check all dates are business days (weekday 0-4)
        for date in unique_dates:
            assert date.weekday() < 5, f"Date {date} is not a business day (weekday={date.weekday()})"

        # Check no gaps: expected n_days unique dates
        assert len(unique_dates) == 100, f"Expected 100 unique dates, got {len(unique_dates)}"

    def test_returns_distribution(self):
        """Test daily close returns: mean ≈ 0 (within ±0.01), std in [0.005, 0.05]."""
        df = generate_ohlcv(n_stocks=20, n_days=500, seed=42)

        # Compute daily returns per stock
        pivot_close = df.pivot(index="date", columns="stock_id", values="close")
        returns = pivot_close.pct_change().dropna()

        # Flatten returns
        all_returns = returns.values.flatten()

        # Mean should be close to 0 (within ±0.01)
        mean_return = np.mean(all_returns)
        assert abs(mean_return) < 0.01, f"Expected mean return close to 0, got {mean_return}"

        # Std should be in [0.005, 0.05]
        std_return = np.std(all_returns)
        assert 0.005 < std_return < 0.05, f"Expected std in [0.005, 0.05], got {std_return}"

    def test_generate_with_custom_params(self):
        """Test configurable n_stocks=10, n_days=100."""
        df = generate_ohlcv(n_stocks=10, n_days=100)

        assert df.shape == (1000, 7)
        assert df["date"].nunique() == 100
        assert df["stock_id"].nunique() == 10

    def test_reproducibility(self):
        """Test same seed produces same data."""
        df1 = generate_ohlcv(n_stocks=10, n_days=50, seed=12345)
        df2 = generate_ohlcv(n_stocks=10, n_days=50, seed=12345)

        # Reset index for comparison
        df1_reset = df1.reset_index(drop=True)
        df2_reset = df2.reset_index(drop=True)

        # Compare all columns
        pd.testing.assert_frame_equal(df1_reset, df2_reset)
