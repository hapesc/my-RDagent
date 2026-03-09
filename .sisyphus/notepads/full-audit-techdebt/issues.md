## Issues

- Pre-existing diagnostics outside plan scope exist in `agentrd_cli.py`, `tests/test_task_10_run_service.py`, and missing optional import resolution for `streamlit`; do not treat them as regressions unless touched by the task.
- The plan file contains many nested acceptance checkboxes; execution tracking should use the 20 top-level tasks (`1-16`, `F1-F4`) as the real sequence.
- If full regression count changes from `548 passed`, evidence/docs must be updated consistently; do not leave stale numbers behind.
- Search findings from planning are advisory; every deletion still requires fresh grep/reference verification immediately before execution.

## Wave 1 Cleanup: Generated __pycache__/.pyc Noise Restoration

- **Issue**: After Wave 1 deletions and test updates completed, test execution generated 109 new `.pyc` cache files tracked in git diff (e.g., `core/__pycache__/*.cpython-313.pyc`, `tests/__pycache__/*.pyc` for all test modules, etc.).
- **Root cause**: Running test suite generates compiled Python bytecode; these are implementation details, not source code.
- **Resolution**: Restored all 109 tracked `.pyc` files to HEAD state via `git checkout HEAD -- <.pyc-files>`, preserving the 9 actual Wave 1 changes:
  - Deleted: `.sisyphus/boulder.json`, `artifact_registry/`, `development_service/`, `execution_service/`
  - Renamed: `.sisyphus/plans/paper-fc2-fc3.md` → (archived)
  - Updated: `tests/test_task_01_core_models.py` (removed dead services from validation list)
- **Verification**: Full pytest run post-cleanup = **548 passed, 3 warnings** (baseline confirmed).
- **Status**: Wave 1 cleanup fallout fully repaired; ready for acceptance.

## Baseline Drift Note

- The historical handoff baseline `548 passed, 3 warnings` is now stale.
- After verified Wave 2 work, current observed healthy baseline is **549 passed, 3 warnings**.
- Future gates should use `>= current healthy baseline` plus `warnings do not increase unexpectedly`, not a hardcoded historical count.

## Task 13: Paper Gap Analysis Contradiction Fix

- **Issue**: `dev_doc/paper_gap_analysis.md` contained 4 self-contradictions where Framework Components claimed "Fully Implemented" status while simultaneously listing "Missing:" bullet points in their Evidence sections.
  - FC-1: "Fully Implemented" vs "Missing: Time budget loop structure, Dynamic method cost estimation, Time-based strategy switching"
  - FC-4: "Fully Implemented" vs "Missing: Embedding-based hypothesis storage, Interaction kernel, Algorithm 2 adaptive selection, Cross-branch knowledge sharing"
  - FC-5: "Fully Implemented" vs "Missing: Debug mode with 10% sampling, Timing estimation, Multi-stage evaluation checks"
  - FC-6: "Fully Implemented" vs "Missing: Automated data splitting, Grading script generation, ValidationSelector multi-candidate ranking"

- **Root cause**: Document was authored during progressive implementation phases; status labels ("Fully Implemented") were not updated when actual capabilities were discovered to be incomplete.

- **Resolution**: Updated status labels and gap ratings for FC-1, FC-4, FC-5, FC-6 from "Fully Implemented"/"MINOR" to "Partial Implementation"/"SIGNIFICANT" to accurately reflect current state. Evidence sections reworded to clarify which components exist (storage, config, frameworks) vs. which are missing (integration, algorithm execution, data enforcement). Impact sections updated to describe actual current limitations rather than theoretical ones.

- **Verification**: Grep confirms no remaining FC section claims "Fully Implemented" while simultaneously listing "Missing:" bullets. FC-2 and FC-3 remain "Fully Implemented" with coherent Evidence sections. Document structure and other FCs unchanged.

- **Scope**: 159 lines changed, 84 insertions, 75 deletions. Only `dev_doc/paper_gap_analysis.md` modified; no code changes, no test impact.

## Task 13 Correction: Internal Consistency Fix

- **Initial Error**: First submission fixed section-level contradictions (FC-1/4/5/6 "Fully Implemented" → "Partial Implementation") but failed to update Summary Table and final Status paragraph, creating a new contradiction between section details and summary statements.

- **Root Cause**: Section-level edits were made but rollup sections (Summary Table, Key Insight, Final Status) were not synchronized. This created internal document inconsistency: detailed sections said "Partial Implementation" while table said "Fully implemented" for the same components.

- **Second Submission Fix**:
  - Updated Summary Table ratings: FC-1/4/5/6 changed from MINOR to SIGNIFICANT
  - Updated Summary Table status text for FC-1/4/5/6: changed to "Partial:" prefix
  - Rewrote "Key Insight" to explicitly state FC-2/3 are fully implemented, FC-1/4/5/6 are partial
  - Updated Final Status line to distinguish between fully and partially implemented components

- **Lesson Learned**: When modifying claims at section level, must cascade updates through ALL summary sections (table, key insight, status line) to maintain document-level consistency. A "Partial Implementation" claim in a detailed section cannot coexist with "Fully implemented" in a summary table without creating contradiction.

- **Verification**: All 6 FCs now have consistent status across three levels:
  - Section-level "Current State": FC-1/4/5/6 → Partial, FC-2/3 → Fully
  - Summary Table ratings: FC-1/4/5/6 → SIGNIFICANT, FC-2/3 → MINOR
  - Summary Table status text: FC-1/4/5/6 → "Partial:", FC-2/3 → "Fully implemented:"
  - Key Insight paragraph: Explicitly names which are full vs partial
  - Final Status: Clear distinction between full and partial implementations

## Wave 5 Task 14: grep verification caveat

- The literal check `grep -r "main.py\|orchestrator_rd_loop_engine" dev_doc README.md` is noisy because it also matches the legitimate current entrypoint `app/api_main.py`.
- For actual stale-reference validation, use a stricter pattern that targets standalone `main.py` mentions; otherwise Task-21 current docs produce a false positive.

## Wave 5 Task 14: rejection fix note

- Atlas rejection was valid: `README.md` still contained the stale full-test command `python3 -m unittest discover -s tests -p 'test_*.py'` even though the prior report claimed it was updated.
- Fix applied conservatively: `README.md` now uses the current truthful repo-wide regression command `python3 -m pytest tests -q`; previously touched Task-14 docs were re-checked for the same stale command and required no further edits.

## Wave 5 Task 14: Task-17 matrix follow-up

- Atlas flagged `dev_doc/task_17_test_matrix.md` because it repeated the script's internal `unittest discover` invocation as if it were durable guidance.
- Conservative fix: keep the Task-17 entrypoint `./scripts/run_task17_acceptance.sh`, remove the duplicated internal command from the doc, and leave repo-wide regression guidance on explicit `pytest` wording only.

## Task 9 retry issue: textual compliance vs behavioral green

- A prior Task 9 fix removed the top-level cycle but still left function-local `from scenarios ...` lines in `plugins/__init__.py`.
- Lesson: this plan item is literal, not just behavioral; local direct imports still fail audit even when smoke tests pass.

## Final quality issue: private-state evaluator reconstruction

- The prior Task 9 implementation preserved behavior by peeking into evaluator internals (`vars(evaluator)`) and recreating evaluators with `type(evaluator)(...)`, but this was too tightly coupled to `VirtualEvaluator` private fields and constructor shape.
- Safer rule: `ExplorationManager` should consume the injected evaluator interface only and let runtime/config own evaluator budgeting.
