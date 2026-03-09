"""Quantitative metrics computation: IC, ICIR, Sharpe, MDD, ARR, Calmar."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def compute_ic(
    predicted: pd.Series,
    actual: pd.Series,
    dates: pd.Series,
) -> dict:
    """Pearson IC per cross-section (per date), then averaged.

    IC is computed per date (cross-sectional correlation), not as a time-series correlation.
    This matches the standard quant definition used in the original RDAgent paper.
    """
    df = pd.DataFrame({"predicted": predicted, "actual": actual, "date": dates})
    df = df.dropna(subset=["predicted", "actual"])

    if df.empty:
        return {"ic_mean": float("nan"), "ic_std": float("nan"), "ic_series": pd.Series(dtype=float)}

    def pearson_corr(g: pd.DataFrame) -> float:
        if len(g) < 2:
            return float("nan")
        p = np.asarray(g["predicted"].values, dtype=float)
        a = np.asarray(g["actual"].values, dtype=float)
        if np.std(p) < 1e-10 or np.std(a) < 1e-10:
            return float("nan")
        return float(np.corrcoef(p, a)[0, 1])

    ic_series = df.groupby("date").apply(pearson_corr, include_groups=False)
    ic_series = ic_series.dropna()

    if ic_series.empty:
        return {"ic_mean": float("nan"), "ic_std": float("nan"), "ic_series": ic_series}

    return {
        "ic_mean": float(ic_series.mean()),
        "ic_std": float(ic_series.std()),
        "ic_series": ic_series,
    }


def compute_icir(ic_series: pd.Series) -> float:
    """IC Information Ratio = mean(IC) / std(IC)."""
    ic_series = ic_series.dropna()
    if len(ic_series) < 2:
        return float("nan")
    std = ic_series.std()
    if std < 1e-10:
        return float("nan")
    return float(ic_series.mean() / std)


def compute_rank_ic(
    predicted: pd.Series,
    actual: pd.Series,
    dates: pd.Series,
) -> dict:
    """Spearman Rank IC per cross-section."""
    df = pd.DataFrame({"predicted": predicted, "actual": actual, "date": dates})
    df = df.dropna(subset=["predicted", "actual"])

    if df.empty:
        return {"rank_ic_mean": float("nan"), "rank_ic_std": float("nan"), "rank_ic_series": pd.Series(dtype=float)}

    def spearman_corr(g: pd.DataFrame) -> float:
        if len(g) < 2:
            return float("nan")
        p_rank = np.asarray(g["predicted"].rank().values, dtype=float)
        a_rank = np.asarray(g["actual"].rank().values, dtype=float)
        if np.std(p_rank) < 1e-10 or np.std(a_rank) < 1e-10:
            return float("nan")
        return float(np.corrcoef(p_rank, a_rank)[0, 1])

    rank_ic_series = df.groupby("date").apply(spearman_corr, include_groups=False)
    rank_ic_series = rank_ic_series.dropna()

    if rank_ic_series.empty:
        return {
            "rank_ic_mean": float("nan"),
            "rank_ic_std": float("nan"),
            "rank_ic_series": rank_ic_series,
        }

    return {
        "rank_ic_mean": float(rank_ic_series.mean()),
        "rank_ic_std": float(rank_ic_series.std()),
        "rank_ic_series": rank_ic_series,
    }


def compute_rank_icir(rank_ic_series: pd.Series) -> float:
    """Rank IC Information Ratio = mean(RankIC) / std(RankIC)."""
    return compute_icir(rank_ic_series)


def compute_sharpe(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Annualized Sharpe ratio. Annualization factor sqrt(252) for daily returns."""
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    excess = returns - risk_free / 252.0
    std = excess.std()
    if std < 1e-10:
        return float("nan")
    return float(excess.mean() / std * math.sqrt(252))


def compute_mdd(cumulative_returns: pd.Series) -> float:
    """Maximum drawdown (negative number). Input: cumulative return series (e.g. 0.0 → 0.1 → -0.05)."""
    if len(cumulative_returns) < 2:
        return float("nan")
    wealth = (1.0 + cumulative_returns).cumprod()
    running_max = wealth.cummax()
    drawdown = wealth / running_max - 1.0
    return float(drawdown.min())


def compute_arr(cumulative_returns: pd.Series, n_days: int | None = None) -> float:
    """Annualized Rate of Return. Input: daily returns series."""
    returns = cumulative_returns.dropna()
    if len(returns) < 2:
        return float("nan")
    n = n_days if n_days is not None else len(returns)
    total_return = float((1.0 + returns).prod())
    if total_return <= 0:
        return float("nan")
    return float(total_return ** (252.0 / n) - 1.0)


def compute_calmar(arr: float, mdd: float) -> float:
    """Calmar ratio = ARR / |MDD|."""
    if math.isnan(arr) or math.isnan(mdd):
        return float("nan")
    if abs(mdd) < 1e-10:
        return float("nan")
    return float(arr / abs(mdd))


def compute_all_metrics(
    factor_values: pd.Series,
    actual_returns: pd.Series,
    dates: pd.Series,
    portfolio_returns: pd.Series,
) -> dict:
    """Aggregate all 8 quant metrics into a single dict.

    Args:
        factor_values: Factor signal series (same length as dates)
        actual_returns: Realized next-period returns (same length as dates)
        dates: Date index series (same length as factor_values)
        portfolio_returns: Daily portfolio return series

    Returns:
        Dict with keys: ic_mean, icir, rank_ic_mean, rank_icir, sharpe, mdd, arr, calmar
    """
    ic_result = compute_ic(factor_values, actual_returns, dates)
    ic_series = ic_result.get("ic_series", pd.Series(dtype=float))

    rank_ic_result = compute_rank_ic(factor_values, actual_returns, dates)
    rank_ic_series = rank_ic_result.get("rank_ic_series", pd.Series(dtype=float))

    sharpe = compute_sharpe(portfolio_returns)
    mdd = compute_mdd(portfolio_returns)
    arr = compute_arr(portfolio_returns)
    calmar = compute_calmar(arr, mdd)

    return {
        "ic_mean": ic_result["ic_mean"],
        "ic_std": ic_result["ic_std"],
        "icir": compute_icir(ic_series),
        "rank_ic_mean": rank_ic_result["rank_ic_mean"],
        "rank_ic_std": rank_ic_result["rank_ic_std"],
        "rank_icir": compute_rank_icir(rank_ic_series),
        "sharpe": sharpe,
        "mdd": mdd,
        "arr": arr,
        "calmar": calmar,
    }
