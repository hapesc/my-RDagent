"""Quant scenario constants and configuration."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Metric thresholds — minimum acceptable values for a "useful" factor
# ---------------------------------------------------------------------------

METRIC_THRESHOLDS: dict[str, float] = {
    "sharpe": 0.5,       # Sharpe ratio (annualized)
    "ic": 0.02,          # Information Coefficient (Pearson)
    "icir": 0.3,         # IC Information Ratio = mean(IC) / std(IC)
    "rank_ic": 0.02,     # Rank IC (Spearman)
    "rank_icir": 0.3,    # Rank ICIR
    "arr": 0.03,         # Annualized Rate of Return (3% minimum)
    "mdd": -0.35,        # Max Drawdown — negative convention; threshold = worst allowed
    "calmar": 1.0,       # Calmar ratio = ARR / |MDD|
}

# Primary optimization target (all others are constraints)
PRIMARY_METRIC: str = "sharpe"

# Must-pass constraint metrics (factor fails if ANY of these are violated)
CONSTRAINT_METRICS: list[str] = ["ic", "icir", "mdd"]

# ---------------------------------------------------------------------------
# Backtest configuration
# ---------------------------------------------------------------------------

BACKTEST_CONFIG: dict = {
    "rebalance_freq": "daily",      # Daily portfolio rebalancing
    "train_end": "2021-06-30",      # End of training period (~50% of 500 days from 2020-01-01)
    "test_start": "2021-07-01",     # Start of out-of-sample test period
    "initial_capital": 1_000_000,   # Starting capital ($1M)
    "commission_rate": 0.001,       # 0.1% commission per trade (one-way)
    "slippage_rate": 0.001,         # 0.1% slippage per trade (one-way)
    "top_k": 10,                    # Number of top-factor stocks to long (long-only)
    "bottom_k": 10,                 # Number of bottom-factor stocks to short (long-short)
}

# ---------------------------------------------------------------------------
# Code safety — import whitelist and blacklist
# ---------------------------------------------------------------------------

SAFE_IMPORTS: set[str] = {
    "numpy",
    "pandas",
    "math",
    "statistics",
    "functools",
    "itertools",
    "collections",
    "typing",
}

BLOCKED_IMPORTS: set[str] = {
    "os",
    "subprocess",
    "shutil",
    "requests",
    "urllib",
    "socket",
    "sys",
    "importlib",
    "builtins",
    "pickle",
    "shelve",
    "tempfile",
    "pathlib",
    "glob",
}

# ---------------------------------------------------------------------------
# Computation resource limits
# ---------------------------------------------------------------------------

MAX_FACTOR_COMPUTE_SEC: int = 30    # Max wall-clock seconds for factor computation
MAX_FACTOR_MEMORY_MB: int = 512     # Max memory usage for factor computation (MB)
