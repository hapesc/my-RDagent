---
phase: 25
slug: fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ --timeout=60` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | QA-1: Multi-branch default | unit + integration | `pytest tests/test_routing.py -k branch` | ⬜ W0 | ⬜ pending |
| TBD | TBD | TBD | QA-2: Schema exposure | unit | `pytest tests/test_run_start.py -k exploration` | ⬜ W0 | ⬜ pending |
| TBD | TBD | TBD | QA-3: Copy-paste skeletons | unit | `pytest tests/test_guidance.py -k skeleton` | ⬜ W0 | ⬜ pending |
| TBD | TBD | TBD | QA-4: Stage materialization | unit + integration | `pytest tests/test_stage_transition.py -k materialize` | ⬜ W0 | ⬜ pending |
| TBD | TBD | TBD | QA-5: Outcome field unification | unit | `pytest tests/test_stage_entries.py -k outcome` | ⬜ W0 | ⬜ pending |
| TBD | TBD | TBD | QA-6: disposition → recovery_assessment | unit + grep | `pytest tests/ -k recovery_assessment` | ⬜ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Update existing test files to cover new fields and renamed fields
- [ ] Add test fixtures for multi-branch exploration scenarios
- [ ] Verify Pydantic `extra="forbid"` constraint compatibility in test assertions

*Existing test infrastructure covers framework setup — no new framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Guidance text readability | QA-1, QA-3 | Subjective quality of generated guidance text | Review MCP tool output for clarity and copy-paste usability |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
