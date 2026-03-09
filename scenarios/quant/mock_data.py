"""Synthetic OHLCV data generation using correlated Geometric Brownian Motion."""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional


def generate_ohlcv(
    n_stocks: int = 50,
    n_days: int = 500,
    start_date: str = "2020-01-01",
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic OHLCV data using correlated GBM.

    Uses Geometric Brownian Motion with Cholesky decomposition for correlation.
    
    Args:
        n_stocks: Number of stocks to generate (default 50)
        n_days: Number of trading days per stock (default 500)
        start_date: Start date in YYYY-MM-DD format (default "2020-01-01")
        seed: Random seed for reproducibility (default 42)
    
    Returns:
        DataFrame with columns: [date, stock_id, open, high, low, close, volume]
        Shape: (n_stocks * n_days, 7)
    """
    rng = np.random.default_rng(seed)

    mu = 0.0002  # Daily drift (~5% annual)
    sigma = 0.02  # Daily volatility (~2%)
    s0 = 100.0  # Initial stock price

    # Generate business dates
    dates = pd.bdate_range(start=start_date, periods=n_days)

    # Build correlation matrix with base correlation 0.3
    corr = np.full((n_stocks, n_stocks), 0.3)
    np.fill_diagonal(corr, 1.0)

    # Cholesky decomposition for correlated random shocks
    L = np.linalg.cholesky(corr)

    # Generate uncorrelated standard normal shocks: shape (n_days, n_stocks)
    z = rng.standard_normal((n_days, n_stocks))

    # Apply Cholesky to get correlated shocks
    correlated_z = z @ L.T

    # Generate close prices via GBM: dS = mu*S*dt + sigma*S*dW
    close_prices = np.zeros((n_days, n_stocks))
    close_prices[0] = s0

    for t in range(1, n_days):
        close_prices[t] = close_prices[t - 1] * np.exp(
            (mu - 0.5 * sigma**2) + sigma * correlated_z[t]
        )

    # Derive OHLC from close prices
    open_prices = np.zeros_like(close_prices)
    high_prices = np.zeros_like(close_prices)
    low_prices = np.zeros_like(close_prices)

    for t in range(n_days):
        if t == 0:
            open_prices[t] = s0
        else:
            # Overnight gap: small random walk around previous close
            overnight_gap = rng.normal(0, sigma / 4, n_stocks)
            open_prices[t] = close_prices[t - 1] * np.exp(overnight_gap)

        # Intraday range factor
        intraday_range = np.abs(rng.normal(0, sigma / 2, n_stocks))

        # High: max(open, close) * (1 + intraday_range)
        high_prices[t] = np.maximum(open_prices[t], close_prices[t]) * (
            1 + intraday_range
        )

        # Low: min(open, close) * (1 - intraday_range)
        low_prices[t] = np.minimum(open_prices[t], close_prices[t]) * (
            1 - intraday_range
        )

    # Enforce OHLC constraints
    for t in range(n_days):
        for s in range(n_stocks):
            max_oc = max(open_prices[t, s], close_prices[t, s])
            min_oc = min(open_prices[t, s], close_prices[t, s])
            high_prices[t, s] = max(high_prices[t, s], max_oc)
            low_prices[t, s] = min(low_prices[t, s], min_oc)

    # Generate volume using lognormal distribution
    volumes = np.exp(rng.normal(12, 0.5, (n_days, n_stocks)))

    # Build DataFrame in long format
    data = []
    for s in range(n_stocks):
        stock_id = f"STOCK_{s + 1:03d}"
        for t in range(n_days):
            data.append(
                {
                    "date": dates[t],
                    "stock_id": stock_id,
                    "open": open_prices[t, s],
                    "high": high_prices[t, s],
                    "low": low_prices[t, s],
                    "close": close_prices[t, s],
                    "volume": volumes[t, s],
                }
            )

    df = pd.DataFrame(data)

    # Sort by date, then stock_id
    df = df.sort_values(["date", "stock_id"]).reset_index(drop=True)

    return df
