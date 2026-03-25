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
| **Quick run command** | `python -m pytest tests/test_phase27_*.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_phase27_*.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 27-01-T1 | 01 | 1 | P27-KERNEL, P27-COMPONENT | unit | `pytest tests/test_phase27_interaction_kernel.py -x` | ❌ W0 | ⬜ pending |
| 27-01-T2 | 01 | 1 | P27-COMPONENT | unit | `pytest tests/test_phase27_complementarity.py -x` | ❌ W0 | ⬜ pending |
| 27-02-T1 | 02 | 2 | P27-KERNEL | unit | `pytest tests/test_phase27_global_injection.py -x -k shared_edge` | ❌ W0 | ⬜ pending |
| 27-02-T2 | 02 | 2 | P27-INJECT | unit | `pytest tests/test_phase27_global_injection.py -x` | ❌ W0 | ⬜ pending |
| 27-02-T3 | 02 | 2 | P27-INJECT | unit | `pytest tests/test_phase27_global_injection.py -x -k multi_branch` | ❌ W0 | ⬜ pending |
| 27-03-T1 | 03 | 2 | P27-PRUNE4 | unit | `pytest tests/test_phase27_prune_signal4.py -x` | ❌ W0 | ⬜ pending |
| 27-03-T2 | 03 | 2 | P27-SELECT | unit | `pytest tests/test_phase27_select_parents.py -x` | ❌ W0 | ⬜ pending |
| 27-04-T1 | 04 | 3 | P27-MERGE | unit | `pytest tests/test_phase27_merge_synthesis.py -x -k merge_design` | ❌ W0 | ⬜ pending |
| 27-04-T2 | 04 | 3 | P27-MERGE | unit | `pytest tests/test_phase27_merge_synthesis.py -x` | ❌ W0 | ⬜ pending |
| 27-05-T1 | 05 | 4 | P27-PRUNE4 | unit | `pytest tests/test_phase27_integration.py -x -k prune_signal4` | ❌ W0 | ⬜ pending |
| 27-05-T2 | 05 | 4 | P27-E2E | integration | `pytest tests/test_phase27_integration.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase27_interaction_kernel.py` — covers P27-KERNEL (kernel math, softmax, sampling)
- [ ] `tests/test_phase27_complementarity.py` — covers P27-COMPONENT (coverage distance, cosine similarity)
- [ ] `tests/test_phase27_global_injection.py` — covers P27-INJECT (global best, sharing candidates, SHARED edges)
- [ ] `tests/test_phase27_prune_signal4.py` — covers P27-PRUNE4 (functional preservation)
- [ ] `tests/test_phase27_select_parents.py` — covers P27-SELECT (merge-stage complementary parents)
- [ ] `tests/test_phase27_merge_synthesis.py` — covers P27-MERGE (LLM synthesis, holdout, MERGED edges)
- [ ] `tests/test_phase27_integration.py` — covers P27-E2E (sharing → pruning → merge lifecycle)
- [ ] `v3/ports/embedding_port.py` — StubEmbeddingPort for all tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Merged solution outperforms single branches with real LLM | SC-3 | Requires multi-iteration execution with real LLM and data | Run 3+ branch exploration, trigger merge at budget_ratio >= 0.8, compare holdout scores |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
