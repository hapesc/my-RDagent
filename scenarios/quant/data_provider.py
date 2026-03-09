"""Quant data providers: protocol + YFinance + Mock (test-only)."""
from __future__ import annotations

from typing import List, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class QuantDataProvider(Protocol):
    """Protocol for quant OHLCV data providers."""

    def load(self) -> pd.DataFrame:
        """Return OHLCV DataFrame with columns: [date, stock_id, open, high, low, close, volume]."""
        ...


class YFinanceDataProvider:
    """Production data provider using yfinance.

    Fetches real OHLCV data from Yahoo Finance.
    """

    def __init__(self, tickers: List[str], start: str, end: str) -> None:
        self._tickers = tickers
        self._start = start
        self._end = end

    def load(self) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ImportError(
                "yfinance is required for YFinanceDataProvider. "
                "Install with: pip install yfinance"
            ) from exc

        raw = yf.download(
            tickers=self._tickers,
            start=self._start,
            end=self._end,
            auto_adjust=False,
            progress=False,
            group_by="ticker",
        )

        frames = []
        for ticker in self._tickers:
            try:
                df = raw[ticker].copy()
            except KeyError:
                continue
            df.columns = [c.lower() for c in df.columns]
            needed = {"open", "high", "low", "close", "volume"}
            if not needed.issubset(set(df.columns)):
                continue
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            df = df.reset_index()
            # handle both 'Date' and 'Datetime' index name
            if "Date" in df.columns:
                df = df.rename(columns={"Date": "date"})
            elif "Datetime" in df.columns:
                df = df.rename(columns={"Datetime": "date"})
            df["stock_id"] = ticker
            frames.append(df[["date", "stock_id", "open", "high", "low", "close", "volume"]])

        if not frames:
            raise RuntimeError(
                f"No data returned from yfinance for tickers={self._tickers}, "
                f"start={self._start}, end={self._end}. "
                "Check ticker symbols and date range."
            )

        ohlcv = pd.concat(frames, ignore_index=True)
        ohlcv = ohlcv.sort_values(["date", "stock_id"]).reset_index(drop=True)
        return ohlcv


class MockDataProvider:
    """Test-only data provider using synthetic GBM data.

    DO NOT use in production. For unit/integration tests only.
    """

    def __init__(self, n_stocks: int = 10, n_days: int = 100, seed: int = 42) -> None:
        self._n_stocks = n_stocks
        self._n_days = n_days
        self._seed = seed

    def load(self) -> pd.DataFrame:
        from .mock_data import generate_ohlcv

        return generate_ohlcv(n_stocks=self._n_stocks, n_days=self._n_days, seed=self._seed)
