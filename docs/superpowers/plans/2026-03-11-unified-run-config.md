# Unified Run Config Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move stable run configuration into `config.yaml.run_defaults`, narrow runtime execution to `rdagent run`, and deprecate `cli.py`.

**Architecture:** Extend the config layer with a second config object for default run behavior, then merge it into `agentrd_cli.py run` before building the request DTO. Deprecate `cli.py` into a thin failure path so only one execution entrypoint remains. Keep legacy `--input` support for compatibility.

**Tech Stack:** Python, argparse, dataclasses, unittest/pytest, Markdown docs

---

### Task 1: Add failing tests for unified run defaults and CLI override behavior

**Files:**
- Modify: `tests/test_task_03_cli_contract.py`
- Modify: `tests/test_task_18_v1_contracts.py`
- Modify: `tests/test_cli.py`

- [ ] Write tests that expect `run_defaults` to feed `agentrd_cli.py run`.
- [ ] Write tests that expect `--task-summary` and `--data-source` to override `run_defaults`.
- [ ] Write a deprecation test for `cli.py`.

### Task 2: Add `run_defaults` config model and loaders

**Files:**
- Modify: `app/config.py`

- [ ] Introduce config dataclasses for run defaults and nested stop/input/step overrides.
- [ ] Load `run_defaults` from YAML without breaking existing flat config parsing.
- [ ] Keep top-level runtime config behavior unchanged.

### Task 3: Unify execution entrypoints on `agentrd_cli.py run`

**Files:**
- Modify: `agentrd_cli.py`
- Modify: `cli.py`

- [ ] Add high-frequency CLI flags to `run`.
- [ ] Merge `run_defaults`, CLI flags, and `--input` into one request payload.
- [ ] Deprecate `cli.py` with a clear migration message.

### Task 4: Update docs

**Files:**
- Modify: `README.md`
- Modify: `QUICKSTART.md`
- Modify: `dev_doc/configuration.md`
- Modify: `dev_doc/api_reference.md`
- Modify: `dev_doc/deployment.md`
- Modify: `dev_doc/runbook.md`

- [ ] Document `run_defaults`.
- [ ] Document the single supported run entrypoint.
- [ ] Remove `cli.py` as a recommended runtime path.

### Task 5: Verify the new flow

**Files:**
- Review only

- [ ] Run targeted tests for config merging and CLI behavior.
- [ ] Run `python3.11 agentrd_cli.py run --help`.
- [ ] Run `python3.11 cli.py --help` or equivalent deprecation verification.
