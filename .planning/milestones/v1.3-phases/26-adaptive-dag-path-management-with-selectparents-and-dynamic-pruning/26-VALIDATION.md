---
phase: 26
slug: adaptive-dag-path-management-with-selectparents-and-dynamic-pruning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -q --timeout=60` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -q --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | Contracts | unit | `python -m pytest tests/test_phase26_contracts.py -x -q` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 1 | DAG CRUD | unit | `python -m pytest tests/test_phase26_dag.py -x -q` | ❌ W0 | ⬜ pending |
| 26-02-01 | 02 | 1 | SelectParents | unit | `python -m pytest tests/test_phase26_select_parents.py -x -q` | ❌ W0 | ⬜ pending |
| 26-02-02 | 02 | 1 | Scoring ext | unit | `python -m pytest tests/test_phase26_scoring.py -x -q` | ❌ W0 | ⬜ pending |
| 26-03-01 | 03 | 2 | Multi-signal prune | unit | `python -m pytest tests/test_phase26_pruning.py -x -q` | ❌ W0 | ⬜ pending |
| 26-03-02 | 03 | 2 | Auto-prune trigger | integration | `python -m pytest tests/test_phase26_auto_prune.py -x -q` | ❌ W0 | ⬜ pending |
| 26-04-01 | 04 | 2 | HypothesisSpec | unit | `python -m pytest tests/test_phase26_hypothesis.py -x -q` | ❌ W0 | ⬜ pending |
| 26-04-02 | 04 | 2 | Diversity entropy | unit | `python -m pytest tests/test_phase26_diversity.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase26_contracts.py` — stubs for DAGNodeSnapshot, DAGEdgeSnapshot, NodeMetrics, HypothesisSpec, ApproachCategory
- [ ] `tests/test_phase26_dag.py` — stubs for DAGService CRUD operations
- [ ] `tests/test_phase26_select_parents.py` — stubs for SelectParentsService parent selection
- [ ] `tests/test_phase26_scoring.py` — stubs for generalization_gap and overfitting_risk computation
- [ ] `tests/test_phase26_pruning.py` — stubs for multi-signal pruning criteria
- [ ] `tests/test_phase26_auto_prune.py` — stubs for auto-prune trigger in exploration round
- [ ] `tests/test_phase26_hypothesis.py` — stubs for HypothesisSpec integration
- [ ] `tests/test_phase26_diversity.py` — stubs for Shannon entropy diversity scoring

*Existing infrastructure covers shared fixtures via `tests/conftest.py`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cosine decay curve shape | SelectParents + Pruning | Visual inspection of curve properties | Plot `cosine_decay(x, 0.7, 0.3)` for x in [0,1], verify smooth monotonic decrease |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
