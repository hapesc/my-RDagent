---
phase: 27-cross-branch-communication-and-multi-trace-solution-merge
plan: 04
subsystem: orchestration
tags: [merge, synthesis, dag, holdout, testing]
requires:
  - phase: 27-cross-branch-communication-and-multi-trace-solution-merge
    provides: sharing topology, complementary parent signals, persisted component classes, and branch component-score collection
provides:
  - LLM-style merge synthesis contract with select/modify/create operations
  - complementary merge orchestration with MERGED DAG edges
  - holdout-style merge acceptance gate
affects: [phase27-05, phase28]
tech-stack:
  added: []
  patterns: [complementary pair selection, merge holdout gating, DAG-traced merged outcomes]
key-files:
  created:
    - .planning/phases/27-cross-branch-communication-and-multi-trace-solution-merge/27-04-SUMMARY.md
    - tests/test_phase27_merge_synthesis.py
  modified:
    - v3/algorithms/merge.py
    - v3/orchestration/branch_merge_service.py
key-decisions:
  - "Merge synthesis now returns structured operation/source/component metadata so Phase 27 can distinguish select, modify, and create outcomes without special-casing summary strings."
  - "Complementary merge source selection is driven by component_coverage_distance over the shortlist rather than by raw quality gap alone."
  - "Merged candidates pass through a standalone holdout gate before the outcome is accepted, keeping the gate swappable for Phase 28 without rewriting merge orchestration."
patterns-established:
  - "Merge logic should separate pair selection, synthesis, holdout gating, and DAG topology recording rather than entangling them inside one fallback branch."
  - "When complementary merge tests need to observe weakness filtering and conflict resolution, capture traces at the merger boundary instead of asserting hidden locals."
requirements-completed: [P27-MERGE]
duration: 21min
completed: 2026-03-24
---

# Phase 27 Plan 04: Complementary Merge Synthesis Summary

**Complementary branch pairing, structured merge synthesis, MERGED topology edges, and a holdout-style acceptance gate now exist as one coherent Phase 27 merge pipeline**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-24T02:40:49+08:00
- **Completed:** 2026-03-24T03:01:45+08:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Extended `MergeDesign` and added `LLMTraceMerger`, giving Phase 27 structured merge operations, source provenance, component analysis, and optional holdout scores.
- Added `BranchMergeService.merge_with_complementarity`, which chooses the most complementary shortlist pair, filters weak components, resolves conflicts, records MERGED edges, and rejects underperforming merged candidates.
- Added focused merge synthesis tests covering the merger contract, holdout gate, MERGED edge creation, and component-level conflict elimination.

## Task Commits

Each task was committed atomically where the shared proof surface allowed it:

1. **Task 1 + Task 2: Merge contract extension and complementary merge orchestration** - `88efee9` (feat)

## Files Created/Modified

- `v3/algorithms/merge.py` - Added `LLMTraceMerger`, extended `MergeDesign`, and introduced `validate_merge_holdout`.
- `v3/orchestration/branch_merge_service.py` - Added complementary pair selection, MERGED DAG edges, and holdout-gated merge execution.
- `tests/test_phase27_merge_synthesis.py` - Covers merger behavior, holdout rejection, complementary pair selection, and conflict/weakness filtering.
- `.planning/phases/27-cross-branch-communication-and-multi-trace-solution-merge/27-04-SUMMARY.md` - Captures execution evidence and downstream readiness.

## Decisions Made

- Collapsed merge contract and orchestration landing into one verified change because the meaningful proof spans both `merge.py` and `branch_merge_service.py`.
- Used component coverage distance as the source-pair selector and left semantic/dag-aware extensions to later phases.
- Kept holdout evaluation as an explicit helper so Phase 28 can replace the Phase 27 proxy without changing merge call sites.

## Deviations from Plan

### Auto-fixed Issues

**1. Merge contract and merge orchestration landed together**
- **Found during:** Inline wave-3 execution
- **Issue:** The tests that prove structured merge operations also exercise the complementary orchestration path, so separating Task 1 and Task 2 into isolated commits would have forced an artificial red/green split.
- **Fix:** Landed both layers together in `88efee9` and documented the shared boundary here.
- **Files modified:** `v3/algorithms/merge.py`, `v3/orchestration/branch_merge_service.py`, `tests/test_phase27_merge_synthesis.py`
- **Verification:** `uv run pytest tests/test_phase27_merge_synthesis.py tests/test_phase16_convergence.py -x -q`
- **Committed in:** `88efee9`

---

**Total deviations:** 1 auto-fixed (shared proof surface)
**Impact on plan:** No behavioral scope creep; the merge pipeline shipped exactly the Phase 27 behaviors, but the proof boundary was tighter than the original task split implied.

## Issues Encountered

- One integration test initially used a peer score that sat too close to the dynamic prune threshold, so the expected pre-merge branch set was unstable. The fixture was corrected so the lifecycle test distinguishes duplicate low-quality branches from uniquely useful branches honestly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `27-05` can now assert real MERGED edges, holdout failures, and component-analysis propagation inside end-to-end lifecycle tests.
- Phase 28 can replace the holdout proxy with real calibration logic without reworking the merge service contract.

## Self-Check: PASSED

- Verified `uv run pytest tests/test_phase27_merge_synthesis.py tests/test_phase16_convergence.py -x -q` exits 0.
- Verified commit `88efee9` exists in git history.
- Verified summary file exists at `.planning/phases/27-cross-branch-communication-and-multi-trace-solution-merge/27-04-SUMMARY.md`.

---
*Phase: 27-cross-branch-communication-and-multi-trace-solution-merge*
*Completed: 2026-03-24*
