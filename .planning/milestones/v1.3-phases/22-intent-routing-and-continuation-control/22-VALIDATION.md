---
phase: 22
slug: intent-routing-and-continuation-control
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-22
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest tests/test_phase22_intent_routing.py -q` |
| **Full suite command** | `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_phase21_public_surface_narrative.py tests/test_phase22_intent_routing.py -q && uv run lint-imports` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_phase22_intent_routing.py -q`
- **After every plan wave:** Run `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_phase21_public_surface_narrative.py tests/test_phase22_intent_routing.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 0 | ROUTE-01 | unit | `uv run python -m pytest tests/test_phase22_intent_routing.py -q` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 0 | ROUTE-02 | integration | `uv run python -m pytest tests/test_phase20_stage_skill_contracts.py tests/test_phase21_public_surface_narrative.py tests/test_phase22_intent_routing.py -q` | ✅/❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase22_intent_routing.py` — locks plain-language intent entry, paused-run-first routing, and downshift only when high-level boundary is insufficient

*Existing infrastructure covers all phase requirements once the Phase 22 routing regression file is added.*

---

## Manual-Only Verifications

All phase behaviors should be automatable from persisted state fixtures or file-reading regressions.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
