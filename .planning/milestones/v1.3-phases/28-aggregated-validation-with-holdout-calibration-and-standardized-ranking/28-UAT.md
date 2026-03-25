---
status: complete
phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
source: 28-01-SUMMARY.md, 28-02-SUMMARY.md, 28-03-SUMMARY.md, 28-04-SUMMARY.md
started: 2026-03-24T04:40:00Z
updated: 2026-03-24T04:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Holdout Contract Surface
expected: The Phase 28 exploration contract surface should expose holdout-aware node metrics, ranked final submission contracts, and fold/evaluation ports without circular import failures.
result: pass

### 2. Finalization Pipeline
expected: Finalization should collect frontier and MERGED candidates, evaluate them across holdout folds, rank them by mean holdout score with std tiebreak, and persist the winning submission plus node metrics.
result: pass

### 3. Merge Gate Behavior After Proxy Removal
expected: The obsolete validate_merge_holdout proxy should be absent, while merge-time gating should still reject underperforming merged candidates via inline comparison.
result: pass

### 4. Automatic Budget-Exhaustion Finalization
expected: When exploration reaches current_round >= max_rounds, the exploration-round result should include a finalization_submission instead of silently continuing unbounded exploration.
result: pass

### 5. Explicit Early Finalization
expected: Operators should be able to trigger finalize_early() before budget exhaustion, and the call should either return a FinalSubmissionSnapshot or fail honestly when no holdout finalization service is configured.
result: pass

### 6. Operator Finalization Guidance
expected: Finalization guidance should render the winner node, winning branch, and holdout metrics in the shared operator-guidance text surface rather than hiding them in persistence only.
result: pass

### 7. End-to-End Lifecycle
expected: A full real-service lifecycle should progress from exploration rounds to persisted final submission, preserve ancestry, allow MERGED candidates into ranking, and keep Phase 16/27 regressions green.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

None.
