---
status: resolved
trigger: "QA report found 3+1 code quality issues in v3/orchestration/multi_branch_service.py"
created: 2026-03-24T00:00:00Z
updated: 2026-03-24T00:05:00Z
---

## Current Focus

hypothesis: All 4 issues were straightforward code quality problems with clear fixes
test: Run full test suite (343 tests)
expecting: All pass
next_action: Await human verification

## Symptoms

expected: Clean, maintainable code following project conventions (<50 line functions, specific exception handling, static imports)
actual:
  1. run_exploration_round() is 212 lines (lines 77-288) - far exceeds 50-line guideline
  2. `except Exception:` at line 256 - catches all exceptions including SystemExit/KeyboardInterrupt
  3. `__import__("v3.contracts.tool_io", fromlist=["BranchFallbackRequest"])` at line 330 - dynamic import
  4. `hasattr(self._branch_merge_service, "merge_with_complementarity")` at line 305 - duck typing
errors: No runtime errors - structural/quality issues
reproduction: Read the file and observe the issues directly
started: Accumulated over Phase 28 implementation

## Eliminated

(none - all hypotheses confirmed)

## Evidence

- timestamp: 2026-03-24T00:01:00Z
  checked: v3/contracts/tool_io.py for BranchFallbackRequest
  found: BranchFallbackRequest is defined at line 218, already in __all__
  implication: Static import is safe, no circular dependency

- timestamp: 2026-03-24T00:01:00Z
  checked: v3/contracts does not import from v3/orchestration
  found: No circular dependency exists
  implication: Dynamic import was never necessary

- timestamp: 2026-03-24T00:01:00Z
  checked: BranchMergeService class
  found: merge_with_complementarity is a concrete method on BranchMergeService (line 104)
  implication: hasattr check is redundant - the method always exists on the typed parameter

- timestamp: 2026-03-24T00:02:00Z
  checked: SelectionService.select_next_branch exception types
  found: Raises KeyError (line 48) and ValueError (lines 75, 79)
  implication: except Exception can be narrowed to except (KeyError, ValueError)

- timestamp: 2026-03-24T00:05:00Z
  checked: Full test suite (343 tests)
  found: All 343 pass after refactoring
  implication: Refactoring is behavior-preserving

## Resolution

root_cause: Four independent code quality issues accumulated during Phase 28 development
fix:
  1. Decomposed run_exploration_round (212 lines) into 8 focused helper methods (each <50 lines):
     _validate_first_layer_categories, _prepare_branches, _compute_sharing,
     _dispatch_branches, _build_dag_nodes, _resolve_parent_nodes,
     _compute_node_diversity, _create_sharing_edges, _select_and_prune, _try_finalize
  2. Narrowed `except Exception` to `except (KeyError, ValueError)` matching actual raise sites
  3. Replaced `__import__("v3.contracts.tool_io", ...)` with static import of BranchFallbackRequest
  4. Removed `hasattr(self._branch_merge_service, "merge_with_complementarity")` - method always exists
verification: 343/343 tests pass (full suite), 54/54 targeted tests pass
files_changed: [v3/orchestration/multi_branch_service.py]
