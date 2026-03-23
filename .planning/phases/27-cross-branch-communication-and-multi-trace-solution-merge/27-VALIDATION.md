---
phase: 27
slug: cross-branch-communication-and-multi-trace-solution-merge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | TBD | unit | `python -m pytest tests/test_interaction_kernel.py -x` | ❌ W0 | ⬜ pending |
| 27-01-02 | 01 | 1 | TBD | unit | `python -m pytest tests/test_global_best_injection.py -x` | ❌ W0 | ⬜ pending |
| 27-02-01 | 02 | 2 | TBD | unit | `python -m pytest tests/test_component_classifier.py -x` | ❌ W0 | ⬜ pending |
| 27-02-02 | 02 | 2 | TBD | unit | `python -m pytest tests/test_merge_synthesizer.py -x` | ❌ W0 | ⬜ pending |
| 27-03-01 | 03 | 3 | TBD | integration | `python -m pytest tests/test_cross_branch_integration.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_interaction_kernel.py` — stubs for interaction kernel algorithms
- [ ] `tests/test_global_best_injection.py` — stubs for global best injection
- [ ] `tests/test_component_classifier.py` — stubs for component classification
- [ ] `tests/test_merge_synthesizer.py` — stubs for merge synthesis
- [ ] `tests/test_cross_branch_integration.py` — stubs for end-to-end cross-branch flows

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Merged solution outperforms single branches | SC-3 | Requires multi-iteration execution with real LLM | Run 3+ branch exploration, trigger merge, compare scores |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
