---
phase: 31
slug: finalization-state-interface-enhancement-and-default-external-ports
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_phase31*.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_phase31*.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 1 | FINALIZED enum | unit | `pytest tests/test_phase31_finalized_mode.py -x -q` | ❌ W0 | ⬜ pending |
| 31-01-02 | 01 | 1 | mode write on finalize | unit | `pytest tests/test_phase31_finalized_mode.py -x -q` | ❌ W0 | ⬜ pending |
| 31-01-03 | 01 | 1 | board mode sync | unit | `pytest tests/test_phase31_finalized_mode.py -x -q` | ❌ W0 | ⬜ pending |
| 31-02-01 | 02 | 1 | default ports | unit | `pytest tests/test_phase31_default_ports.py -x -q` | ❌ W0 | ⬜ pending |
| 31-02-02 | 02 | 1 | holdout split | unit | `pytest tests/test_phase31_default_ports.py -x -q` | ❌ W0 | ⬜ pending |
| 31-02-03 | 02 | 1 | evaluation port | unit | `pytest tests/test_phase31_default_ports.py -x -q` | ❌ W0 | ⬜ pending |
| 31-02-04 | 02 | 1 | embedding port | unit | `pytest tests/test_phase31_default_ports.py -x -q` | ❌ W0 | ⬜ pending |
| 31-03-01 | 03 | 2 | graceful degradation | integration | `pytest tests/test_phase31_entry_wiring.py -x -q` | ❌ W0 | ⬜ pending |
| 31-03-02 | 03 | 2 | branch_list merge | integration | `pytest tests/test_phase31_entry_wiring.py -x -q` | ❌ W0 | ⬜ pending |
| 31-03-03 | 03 | 2 | CLI tools | integration | `pytest tests/test_phase31_entry_wiring.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase31_finalized_mode.py` — stubs for FINALIZED enum, mode write, board sync
- [ ] `tests/test_phase31_default_ports.py` — stubs for default port implementations
- [ ] `tests/test_phase31_entry_wiring.py` — stubs for entry-layer changes, CLI tools, branch_list

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
