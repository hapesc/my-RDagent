## Decisions

- Use the current repository path `/Users/michael-liang/Code/my-RDagent` as the active git worktree for this session.
- Follow TDD for every implementation task: failing test first when code/test changes are required.
- Delete dead placeholder modules directly instead of moving them to `deprecated/`.
- Keep `.sisyphus/evidence/` intact; only clean stale tracking metadata and archive the unused plan file.
- Handle `reasoning_service/` in two phases: migrate callers first, delete directory later.
- Fix all five production `hasattr` call sites, but do it with explicit capabilities/interfaces and no API churn in `plugins/contracts.py`.
- Break import cycles with minimal surgery: move scenario registration responsibility to runtime wiring, not a broad architecture rewrite.
- Use `app/config.py` as the single source of truth for env-var documentation.
- Wave 1 metadata cleanup (2026-03-08): Deleted stale `.sisyphus/boulder.json` (pointing to old FC-2/FC-3 tracker) and archived `paper-fc2-fc3.md` → `ARCHIVED-paper-fc2-fc3.md` to remove tracking drift. Preserved `.sisyphus/evidence/`, `.sisyphus/plans/paper-fc23-upgrade.md`, and all active evidence. This unblocks clean execution of 20 top-level Wave 1 tasks.


- Task 8 capability cleanup uses explicit optional protocols plus guard functions instead of forcing methods onto all exploration-manager implementations.
- Guard strategy intentionally checks class-level concrete methods (not dynamic attribute synthesis), preventing false positives from `Mock` while preserving behavior for legacy reduced doubles.

- Task 9 uses the smallest safe cut: lazy imports in `plugins/__init__.py` instead of moving registry ownership out of the plugins module, and duck-typed evaluator usage in `exploration_manager/service.py` instead of importing the concrete `VirtualEvaluator` class.
- Task 15 uses a new isolated smoke suite `tests/test_app_smoke.py` rather than expanding existing Task-21/23 tests, so coverage stays centered on the five app entry modules and avoids accidental control-plane regression churn.
