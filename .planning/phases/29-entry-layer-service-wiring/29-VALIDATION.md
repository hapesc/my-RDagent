---
phase: 29
slug: entry-layer-service-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/pytest tests/test_phase29_entry_wiring.py -x -q` |
| **Full suite command** | `.venv/bin/pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/pytest tests/test_phase29_entry_wiring.py -x -q`
- **After every plan wave:** Run `.venv/bin/pytest tests/test_phase28_integration.py tests/test_phase29_entry_wiring.py tests/test_phase16_rd_agent.py -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 1 | P28-HOLDOUT | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_multi_branch_service_receives_holdout_service -x` | ❌ W0 | ⬜ pending |
| 29-01-02 | 01 | 1 | P28-ACTIVATE | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_auto_finalization_triggers_through_entry -x` | ❌ W0 | ⬜ pending |
| 29-01-03 | 01 | 1 | P28-SUBMIT | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_finalization_submission_in_response -x` | ❌ W0 | ⬜ pending |
| 29-01-04 | 01 | 1 | P28-PRESENT | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_finalization_guidance_in_response -x` | ❌ W0 | ⬜ pending |
| 29-01-05 | 01 | 1 | P27-KERNEL | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_branch_share_service_injected -x` | ❌ W0 | ⬜ pending |
| 29-01-06 | 01 | 1 | P27-INJECT | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_global_best_injection_through_entry -x` | ❌ W0 | ⬜ pending |
| 29-01-07 | 01 | 1 | GUIDE-05 | e2e integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_e2e_rd_agent_to_winner -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase29_entry_wiring.py` — stubs for all 7 requirements; no conftest changes needed (existing ArtifactStateStore + StubHoldoutSplitPort + StubEvaluationPort are sufficient)

*Existing infrastructure covers shared fixtures.*

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
