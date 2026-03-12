"""
Quant E2E wrapper: fetch OHLCV data from yfinance, hand off to the unified CLI.

Usage:
    python scripts/run_quant_e2e.py
    python scripts/run_quant_e2e.py --tickers QQQ,VOO,GOOG --start-date 2023-01-01 --end-date 2024-12-31
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from scenarios.quant.data_provider import YFinanceDataProvider

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TICKERS = "QQQ,VOO,GOOG,GLD,SLV,SCHD"
DEFAULT_START_DATE = "2022-01-01"
DEFAULT_END_DATE = "2024-12-31"
DEFAULT_TASK_SUMMARY = (
    "Mine a single alpha factor using price/volume data for QQQ, VOO, GOOG, GLD, SLV, SCHD. "
    "The factor should predict next-day returns. Avoid look-ahead bias."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("quant_e2e")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quant E2E wrapper: yfinance prefetch + unified CLI execution")
    parser.add_argument("--tickers", default=DEFAULT_TICKERS, help="Comma-separated ticker list")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE, help="Inclusive start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=DEFAULT_END_DATE, help="Inclusive end date (YYYY-MM-DD)")
    parser.add_argument("--task-summary", default=DEFAULT_TASK_SUMMARY, help="Task description passed to quant run")
    parser.add_argument("--max-loops", type=int, default=1, help="Max loop iterations for the quant run")
    return parser.parse_args(argv)


def _parse_tickers(raw: str) -> list[str]:
    tickers = [item.strip() for item in raw.split(",") if item.strip()]
    if not tickers:
        raise ValueError("at least one ticker is required")
    return tickers


def _write_temp_ohlcv_csv(frame) -> Path:
    with tempfile.NamedTemporaryFile(prefix="rdagent-quant-", suffix=".csv", delete=False) as handle:
        temp_path = Path(handle.name)
    frame.to_csv(temp_path, index=False)
    return temp_path


def _build_cli_command(
    *,
    config_path: Path,
    data_source: Path,
    task_summary: str,
    max_loops: int,
) -> list[str]:
    return [
        sys.executable,
        str(PROJECT_ROOT / "agentrd_cli.py"),
        "run",
        "--config",
        str(config_path),
        "--scenario",
        "quant",
        "--task-summary",
        task_summary,
        "--data-source",
        str(data_source),
        "--max-loops",
        str(max_loops),
        "--loops-per-call",
        str(max_loops),
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tickers = _parse_tickers(args.tickers)

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    log.info("=== Quant E2E Wrapper ===")
    log.info("Tickers   : %s", tickers)
    log.info("Date range: %s → %s", args.start_date, args.end_date)
    log.info("Task      : %s", args.task_summary)
    log.info("Max loops : %d", args.max_loops)

    log.info("[1/3] Fetching OHLCV data via yfinance...")
    provider = YFinanceDataProvider(
        tickers=tickers,
        start=args.start_date,
        end=args.end_date,
    )
    frame = provider.load()
    log.info(
        "      Data fetched: %d rows, %d tickers, date range %s → %s",
        len(frame),
        frame["stock_id"].nunique(),
        str(frame["date"].min())[:10],
        str(frame["date"].max())[:10],
    )

    temp_csv: Path | None = None
    try:
        log.info("[2/3] Writing temporary OHLCV csv...")
        temp_csv = _write_temp_ohlcv_csv(frame)
        log.info("      Temp csv: %s", temp_csv)

        log.info("[3/3] Running unified quant CLI...")
        cmd = _build_cli_command(
            config_path=config_path,
            data_source=temp_csv,
            task_summary=args.task_summary,
            max_loops=args.max_loops,
        )
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            raise SystemExit(result.returncode)
        return 0
    finally:
        if temp_csv is not None and temp_csv.exists():
            temp_csv.unlink()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
