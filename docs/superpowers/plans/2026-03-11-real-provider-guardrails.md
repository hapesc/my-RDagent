# Real Provider Guardrails Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove blocking hard limits from real-provider guardrails while keeping warning-based operator feedback.

**Architecture:** Keep conservative-profile metadata and warning generation in `app/config.py`, but eliminate `ValueError` branches tied to performance-only thresholds. Preserve only invalid-shape validation (`layer0_k_forward > layer0_n_candidates`).

**Tech Stack:** Python, unittest, config/runtime wiring

---

### Task 1: Write failing tests for non-blocking guardrails

**Files:**
- Modify: `tests/test_runtime_wiring.py`
- Modify: `tests/test_integration_full_loop.py`

- [ ] Replace tests that expect hard-limit exceptions with tests that expect warnings.
- [ ] Keep invalid-shape validation tests unchanged.

### Task 2: Remove hard-limit enforcement

**Files:**
- Modify: `app/config.py`

- [ ] Remove hard-limit constants and exception branches for performance-only thresholds.
- [ ] Update warning text to mention long execution time.

### Task 3: Verify targeted runtime behavior

**Files:**
- Review only

- [ ] Run focused runtime-wiring and integration tests.
- [ ] Re-run `python3.11 -m app.startup --config ./config.yaml` to confirm the original symptom is gone.
