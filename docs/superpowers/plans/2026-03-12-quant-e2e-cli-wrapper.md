# Quant E2E CLI Wrapper Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `scripts/run_quant_e2e.py` fetch yfinance data and delegate execution to the unified quant CLI path.

**Architecture:** The script will be reduced to a wrapper around `YFinanceDataProvider` plus a subprocess call into `agentrd_cli.py run`. A temporary OHLCV CSV is the handoff artifact between the prefetch stage and the normal quant runtime path. Tests will verify command construction and cleanup.

**Tech Stack:** Python, argparse, pandas, subprocess, tempfile, pytest

---

### Task 1: Write failing tests for wrapper behavior

**Files:**
- Create: `tests/test_run_quant_e2e_script.py`

- [ ] Write a test that expects the script to call `agentrd_cli.py run` with `--scenario quant` and `--data-source`.
- [ ] Write a test that expects the temporary CSV to be deleted after success.
- [ ] Write a test that expects the temporary CSV to be deleted after CLI failure.

### Task 2: Refactor the script into a thin wrapper

**Files:**
- Modify: `scripts/run_quant_e2e.py`

- [ ] Replace inline runtime assembly with yfinance fetch + temp CSV write + subprocess call.
- [ ] Add the five supported CLI flags.
- [ ] Reuse `config.yaml` from the repository root.

### Task 3: Update docs

**Files:**
- Modify: `README.md`
- Modify: `QUICKSTART.md`

- [ ] Clarify that `scripts/run_quant_e2e.py` is a yfinance wrapper over the normal CLI path.
- [ ] Keep the direct local-CSV quant path as the primary recommendation.

### Task 4: Verify behavior

**Files:**
- Review only

- [ ] Run the new script tests.
- [ ] Run existing quant CLI regression tests.
