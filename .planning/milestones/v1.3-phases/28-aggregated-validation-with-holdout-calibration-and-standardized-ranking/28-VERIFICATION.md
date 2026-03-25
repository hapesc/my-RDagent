---
phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
verified: 2026-03-24T23:02:15+08:00
status: passed
score: 3/3 phase truths verified
---

# Phase 28: Aggregated Validation with Holdout Calibration and Standardized Ranking Verification Report

**Phase Goal:** Implement the final layer of the R&D-Agent convergence mechanism: K-fold holdout calibration, parallel re-evaluation via abstract ports, and standardized ranking for final submission selection.
**Verified:** 2026-03-24T23:02:15+08:00
**Status:** passed
**Verification scope:** executed code, Phase 28 plan and summary artifacts, targeted Phase 28 regression suites, Phase 29 entry-layer regression evidence, and requirements traceability.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Top candidates are collected for final evaluation from frontier plus MERGED nodes through one canonical collection path. | ✓ VERIFIED | `v3/algorithms/holdout.py` exports `collect_candidate_ids`; `v3/orchestration/holdout_validation_service.py` uses it during finalization; `tests/test_phase28_holdout_service.py` and `tests/test_phase28_integration.py` are included in the green Phase 28 suite and verify merged-node collection and ranked submission assembly. |
| 2 | K-fold holdout evaluation prevents overfitting to the immediate exploration score by routing finalization through abstract split/evaluation ports and persisting calibrated holdout metrics. | ✓ VERIFIED | `v3/ports/holdout_port.py` defines `HoldoutSplitPort`, `EvaluationPort`, and `StratifiedKFoldSplitter`; `v3/orchestration/holdout_validation_service.py` performs fold evaluation and writes `holdout_mean` / `holdout_std` to DAG nodes and `FinalSubmissionSnapshot`; `uv run pytest tests/test_phase28_holdout_ports.py tests/test_phase28_ranking.py tests/test_phase28_holdout_service.py tests/test_phase28_activation.py tests/test_phase28_integration.py -x -q` passed with `39 passed in 0.41s`. |
| 3 | Standardized ranking and finalization produce one authoritative winning submission, and that submission is reachable through the real entry layer. | ✓ VERIFIED | `v3/algorithms/holdout.py` implements `rank_candidates`; `v3/orchestration/multi_branch_service.py` triggers `_try_finalize()` and exposes `finalize_early()`; `v3/orchestration/operator_guidance.py` renders the finalization summary; `v3/entry/rd_agent.py` surfaces `finalization_submission` and `finalization_guidance`; `uv run pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase29_entry_wiring.py tests/test_phase16_rd_agent.py tests/test_phase26_integration.py tests/test_phase27_global_injection.py tests/test_phase27_integration.py tests/test_phase28_integration.py -x -q` passed with `55 passed in 0.65s`. |

**Score:** 3/3 phase truths verified

### Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| `P28-HOLDOUT` | ✓ SATISFIED | `v3/ports/holdout_port.py` defines the abstract split/evaluation ports and default splitter; `v3/orchestration/holdout_validation_service.py` orchestrates K-fold evaluation; the green 39-test suite includes `tests/test_phase28_holdout_ports.py`, `tests/test_phase28_holdout_service.py`, and `tests/test_phase28_integration.py`. |
| `P28-RANK` | ✓ SATISFIED | `v3/algorithms/holdout.py` implements `rank_candidates`; `v3/contracts/exploration.py` adds `holdout_mean` and `holdout_std` to ranking contracts; the green 39-test suite includes `tests/test_phase28_ranking.py`. |
| `P28-COLLECT` | ✓ SATISFIED | `v3/algorithms/holdout.py` implements deduplicated `collect_candidate_ids`; `v3/orchestration/holdout_validation_service.py` uses it to collect frontier plus `MERGED` candidates; `tests/test_phase28_holdout_service.py` and `tests/test_phase28_integration.py` verify merged candidates reach the final ranked pool. |
| `P28-ACTIVATE` | ✓ SATISFIED | `v3/orchestration/multi_branch_service.py` triggers `_try_finalize()` when `current_round` reaches `max_rounds` and exposes `finalize_early()`; the green 39-test suite includes `tests/test_phase28_activation.py` and `tests/test_phase28_integration.py`; the green 55-test Phase 29 bundle proves the activation path reaches `rd_agent()`. |
| `P28-REPLACE` | ✓ SATISFIED | `v3/orchestration/branch_merge_service.py` now uses the inline `holdout_score >= best_single_score` gate instead of the removed proxy path; `v3/orchestration/holdout_validation_service.py` owns real holdout evaluation; the green 39-test suite includes `tests/test_phase28_holdout_service.py` and the green 55-test bundle includes `tests/test_phase29_entry_wiring.py`. |
| `P28-SUBMIT` | ✓ SATISFIED | `v3/contracts/exploration.py` defines `FinalSubmissionSnapshot`; `v3/ports/state_store.py` and `v3/orchestration/artifact_state_store.py` persist it through `write_final_submission` / `load_final_submission`; `tests/test_phase28_holdout_service.py` and `tests/test_phase28_integration.py` verify persistence and ancestry traceability. |
| `P28-PRESENT` | ✓ SATISFIED | `v3/orchestration/operator_guidance.py` builds the finalization presentation; `v3/entry/rd_agent.py` exposes `finalization_guidance` and `finalization_submission`; `tests/test_phase28_activation.py`, `tests/test_phase28_integration.py`, and `tests/test_phase29_entry_wiring.py` verify the rendered winner and leaderboard details. |

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-01-SUMMARY.md` to `28-04-SUMMARY.md` | Execution evidence for contracts, holdout service, activation, guidance, and lifecycle validation | ✓ VERIFIED | All four summaries exist and collectively cover the typed holdout surface, finalization service, activation/guidance wiring, and the real-service lifecycle test. |
| `v3/orchestration/holdout_validation_service.py` | Production finalization pipeline over split/evaluation ports | ✓ VERIFIED | File exists and is exercised by the green 39-test Phase 28 suite. |
| `v3/contracts/exploration.py` and `v3/ports/state_store.py` | Ranked submission contract and persistence boundary | ✓ VERIFIED | `FinalSubmissionSnapshot`, `holdout_mean`, `holdout_std`, `write_final_submission`, and `load_final_submission` all exist in production code. |
| `.planning/phases/29-entry-layer-service-wiring/29-VERIFICATION.md` | Entry-layer proof that Phase 28 finalization reaches the public `rd_agent` surface | ✓ VERIFIED | File exists with `status: passed` and cites the green 55-test entry-layer regression bundle. |

### Automated Checks

| Command | Result | Evidence |
| --- | --- | --- |
| `uv run pytest tests/test_phase28_holdout_ports.py tests/test_phase28_ranking.py tests/test_phase28_holdout_service.py tests/test_phase28_activation.py tests/test_phase28_integration.py -x -q` | ✓ PASSED | 39/39 tests passed in 0.41s. |
| `uv run pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase29_entry_wiring.py tests/test_phase16_rd_agent.py tests/test_phase26_integration.py tests/test_phase27_global_injection.py tests/test_phase27_integration.py tests/test_phase28_integration.py -x -q` | ✓ PASSED | 55/55 tests passed in 0.65s, proving Phase 28 finalization remains reachable and truthful through the public entry layer. |
| `rg -n "class HoldoutSplitPort|class EvaluationPort|class StratifiedKFoldSplitter|class HoldoutValidationService|def rank_candidates|def collect_candidate_ids|FinalSubmissionSnapshot|build_finalization_guidance|finalize_early|finalization_submission|write_final_submission|load_final_submission" v3 tests -S` | ✓ PASSED | Confirms the required Phase 28 split/evaluation ports, ranking helpers, submission contract, persistence path, activation hooks, and presentation hooks are present in production code and tests. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `v3/orchestration/holdout_validation_service.py` | `v3/algorithms/holdout.py` | `collect_candidate_ids()` and `rank_candidates()` inside `finalize()` | ✓ WIRED | Candidate collection and ranking live in one canonical algorithm surface. |
| `v3/orchestration/multi_branch_service.py` | `v3/orchestration/holdout_validation_service.py` | `_try_finalize()` and `finalize_early()` | ✓ WIRED | Finalization is reachable both automatically at budget exhaustion and through an explicit operator path. |
| `v3/orchestration/holdout_validation_service.py` | `v3/orchestration/artifact_state_store.py` | `write_final_submission()` / `load_final_submission()` persistence | ✓ WIRED | The winning submission is stored as a first-class artifact, not hidden in transient state. |
| `v3/entry/rd_agent.py` | `v3/orchestration/operator_guidance.py` | `build_finalization_guidance()` plus `finalization_submission` projection | ✓ WIRED | Phase 28 finalization results are surfaced through the public entry response, as verified again in Phase 29. |

### Human Verification Required

None. Phase 28 truth is deterministic service orchestration plus public response wiring, and both the dedicated Phase 28 suite and the Phase 29 entry-layer regression bundle are green.

### Remaining Risks

| Risk | Impact | Status |
| --- | --- | --- |
| Full peer-sharing activation from the public entry surface still depends on embedding-port availability, which is Phase 29 follow-up debt rather than a Phase 28 finalization failure. | Does not block holdout finalization, ranking, persistence, or presentation truth. | Non-blocking follow-up debt. |

### Gaps Summary

No blocking gaps found. Phase 28 achieved holdout calibration, candidate collection, standardized ranking, finalization activation, proxy replacement, submission persistence, and operator presentation with both service-level and entry-layer evidence.

---

_Verified: 2026-03-24T23:02:15+08:00_
_Verifier: Codex (manual execute-phase fallback)_
