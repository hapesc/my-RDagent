# Codebase Concerns

**Analysis Date:** 2026-03-21

## Tech Debt
- `v3/orchestration/artifact_state_store.py:23-218` continues to treat every run/branch/stage/artifact as a pair of `Path.write_text` calls with no locking or atomic rename, so concurrent agents writing the same run or branch (multi-branch rounds, CLI tooling, or parallel test runs) can stomp each other and yield missing snapshots. Consider introducing atomic temp files, lockfiles, or an append-only log before JSON extraction.
- `v3/orchestration/branch_workspace_manager.py:11-30` deletes and copies entire workspaces on each fork via `shutil.rmtree` + `shutil.copytree` without backoff, checksum, or concurrency guards, which is brittle for large checkouts and races with `multi_branch_service` dispatchers that reuse `workspace_root`. A more incremental copy or copy-on-write cache would reduce disk churn and reduce the blast radius of stray branches.

## Known Bugs
- `v3/orchestration/selection_service.py:45-120` always reraises `ValueError` from `PuctSelectionAdapter.select_next_branch` when the adapter cannot decide, leaving `MultiBranchService.run_exploration_round` (which does not catch it) to fail the entire round. Provide a fallback recommendation or wrap the adapter result before it propagates to the caller.
- `v3/orchestration/branch_merge_service.py:36-130` asserts `lead_branch` and `runner_branch` after loading from `StateStorePort` without retrying; partial persistence (common when `ArtifactStateStore` is stressed) results in `AssertionError` and an unhandled crash during convergence. Guard against missing snapshots and record diagnostic errors instead of letting assertions escape production paths.

## Security Considerations
- `scripts/install_agent_skills.py:33-189` blindly links or copies the repository’s `skills/` tree into `~/.codex/skills` and `~/.claude/skills` even when `--global` is set, which can overwrite unrelated skills or expose repo-local files in a shared home directory. Harden the installer by validating the destination and warning when non-managed directories already exist.

## Performance Bottlenecks
- `v3/orchestration/artifact_state_store.py:145-169` enumerates `sorted(base.rglob("*.json"))` every time `list_artifact_snapshots` runs, so larger runs with thousands of artifacts pay a quadratic billing for every query. A sharded index or precomputed manifest per run would keep artifact listing predictable.

## Fragile Areas
- `v3/orchestration/multi_branch_service.py:21-136` is the only place that drives parallel exploration and convergence, yet no test file imports `v3.orchestration.multi_branch_service` (the suite covers `SelectionService` via `tests/test_phase16_selection.py:59-171` but never this module). This makes multi-branch behavior a regression hazard; add dedicated tests that exercise fork/fallback flows.

## Scaling Limits
- The artifact/branch/stage state tree under `ArtifactStateStore` grows unbounded (each stage writes both `branches/<branch>/stages/<stage>.json` and iteration history at `branches/<branch>/stages/<stage>/<iteration>.json`). Without retention or compaction, disk usage balloons as runs accumulate; add cleanup policies or archive thresholds to keep the `.state` workspace manageable (`v3/orchestration/artifact_state_store.py:48-205`).

## Dependencies at Risk
- `v3/orchestration/selection_service.py:45-120` hardcodes `PUCTBranchCandidate` math and only allows configuration through `PuctSelectionAdapter(c_puct=1.41)`. If the upstream `v3.algorithms.puct` API changes or requires tuning, the service has no pluggable abstraction other than swapping adapters, so it will fail silently when the adapter signature drifts. Consider defining an explicit adapter interface in this repository.

## Missing Critical Features
- There is no telemetry or health hook around the filesystem-backed state store; all `StateStorePort` usages rely on `ArtifactStateStore` and the OCaml-like path validation in `v3/orchestration/branch_isolation_service.py:10-78`. When the store becomes stale or FDs are exhausted, the runners just raise `ValueError` and abort. Adding a health check or wrapping writes with retries would make investigations more actionable.

## Test Coverage Gaps
- `tests/test_phase16_selection.py:59-171` exercises `SelectionService` but nothing exercises `MultiBranchService` or its interaction with `BranchMergeService`/`BranchLifecycleService`. A grep over `tests/` shows no imports of `v3.orchestration.multi_branch_service`, so the multi-branch path is effectively untested and can regress without detection. Add targeted tests (e.g., `tests/test_phase16_multi_branch.py`) before iterating on exploration features.

---
*Concerns audit: 2026-03-21*
