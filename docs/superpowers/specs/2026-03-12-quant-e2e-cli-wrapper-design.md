# Quant E2E CLI Wrapper Design

## Goal

Refactor `scripts/run_quant_e2e.py` so it no longer assembles its own runtime. The script should only fetch OHLCV data from yfinance, write a temporary CSV in the standard quant format, invoke the unified `agentrd run` path, and delete the temporary file afterwards.

## Decisions

- Keep the script as a yfinance convenience wrapper, not a second runtime entrypoint.
- Expose only five user-facing parameters:
  - `--tickers`
  - `--start-date`
  - `--end-date`
  - `--task-summary`
  - `--max-loops`
- Use the repository root `config.yaml` as the runtime config source; do not add separate model/provider flags to the script.
- Write OHLCV data to a temporary CSV with the canonical quant schema:
  `date,stock_id,open,high,low,close,volume`
- Invoke the unified CLI using `python agentrd_cli.py run ...`.
- Always delete the temporary CSV in a `finally` block, regardless of success or failure.

## Non-Goals

- No new HTTP/API behavior
- No new yfinance configuration system beyond the five script flags
- No alternate in-memory handoff path
