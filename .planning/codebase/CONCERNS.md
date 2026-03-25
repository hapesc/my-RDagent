# Codebase Concerns

**Analysis Date:** 2026-03-25

## Persistence Risks

- `v3/orchestration/artifact_state_store.py` writes canonical run/branch/stage/artifact/DAG JSON files directly via filesystem paths but does not add locking, atomic rename staging, or corruption recovery. That is fine for deterministic local tests, but it is a structural risk if multiple writers touch the same state root or if a write is interrupted mid-file.
- The same store relies on repeated directory scans such as `sorted(base.rglob("*.json"))` in artifact listing paths. As the number of runs, artifacts, DAG nodes, and decisions grows, read cost scales with directory size rather than with an indexed manifest.

## Workspace and Filesystem Churn

- `v3/orchestration/branch_workspace_manager.py` recreates branch workspaces by deleting the existing directory with `shutil.rmtree` and then copying or recreating from scratch. That is a blunt but simple strategy; it increases IO cost and makes accidental reuse/state loss harder to reason about when exploration rounds get larger.
- Repo-local install flows intentionally materialize `.claude/` and `.codex/` inside the repository through `v3/devtools/skill_install.py` and `scripts/setup_env.sh`. That is useful for self-contained runtime testing, but it also means repo hygiene depends on `.gitignore` staying correct. If ignore rules drift, generated runtime bundles and installed skills will pollute the working tree.

## Coordination Complexity

- `v3/orchestration/multi_branch_service.py` is a high-leverage coordinator that composes selection, pruning, DAG updates, sharing, parent selection, merge/finalization, and dispatcher behavior. The repo has meaningful tests around this area, but the service still concentrates a lot of orchestration authority in one file, so future changes there have a disproportionate blast radius.
- Several later-phase capabilities are optional by design (`EmbeddingPort`, holdout validation, branch sharing, finalization). This makes graceful degradation possible, but it also increases the number of wiring combinations that can silently diverge in behavior if one dependency is absent or injected incorrectly.

## Observability Gaps

- The public surface is strong on structured return payloads, but the runtime does not have a real logging, metrics, or tracing subsystem. When branch selection, finalization, or installer flows behave unexpectedly, the main debugging tools are tests plus direct state inspection of JSON snapshots under the state root.
- Preflight is helpful for dependency/runtime blockers, but it is not a replacement for operational telemetry. It can tell the operator that the environment is blocked; it cannot tell them how often a write race, workspace churn, or degraded optional dependency path is happening in practice.

## Verification Gaps

- The suite is broad, but it is still mostly deterministic and local. External seams such as execution, embeddings, and holdout evaluation are validated through stubs/fakes rather than through real backend integrations.
- There is no dedicated concurrency or soak testing for the filesystem-backed state store, branch workspaces, or repeated multi-branch rounds.
- CI runs only on macOS and Linux (`.github/workflows/ci.yml`), so Windows-specific path, shell, or symlink behavior would currently slip through.

## Maintainability Pressure Points

- `v3/entry/tool_catalog.py` centralizes a large amount of metadata, request/response wiring, examples, and follow-up semantics in one registry module. That centralization is good for consistency, but it makes the file a maintenance hotspot as the direct-tool surface grows.
- The repository carries both executable Python surfaces and human-facing skill/workflow artifacts. That is the correct product shape here, but it means any behavior change often requires synchronized updates across `v3/`, `skills/`, README guidance, and contract tests. Drift is controlled by tests, yet the coordination cost is real.

## Strict-Path Recommendation

- If this repo evolves toward heavier unattended or concurrent execution, the first structural upgrades should be: atomic state-store writes, better indexing for persisted artifacts, and more explicit observability around multi-branch orchestration paths.
- The dangerous mistake here would be to paper over filesystem or coordination weaknesses with ad hoc retries and fallback heuristics. The architecture is clean enough that it should stay strict: fix the state/persistence model rather than hiding inconsistency behind “best effort” continuation.

---

*Concerns audit: 2026-03-25*
