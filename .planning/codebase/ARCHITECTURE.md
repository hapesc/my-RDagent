# Architecture

**Analysis Date:** 2026-03-25

## Pattern Overview

**Overall:** Contract-first layered orchestration runtime with dual public surfaces: skill packages under `skills/` for agent-facing use and Python/CLI entrypoints under `v3/entry/` for executable use.

**Key Characteristics:**
- `skills/rd-agent/SKILL.md`, `skills/rd-propose/SKILL.md`, `skills/rd-code/SKILL.md`, `skills/rd-execute/SKILL.md`, `skills/rd-evaluate/SKILL.md`, and `skills/rd-tool-catalog/SKILL.md` are the operator-facing boundary; each maps directly to code in `v3/entry/`.
- `v3/contracts/` is the schema spine. Pydantic models in `v3/contracts/run.py`, `v3/contracts/branch.py`, `v3/contracts/stage.py`, `v3/contracts/exploration.py`, `v3/contracts/memory.py`, `v3/contracts/preflight.py`, and `v3/contracts/tool_io.py` define the stable data model before services mutate anything.
- `v3/orchestration/` owns behavior, `v3/tools/` is a thin adapter layer, and `v3/ports/` defines external seams. Concrete filesystem adapters stay in `v3/orchestration/artifact_state_store.py`, `v3/orchestration/memory_state_store.py`, and `v3/orchestration/branch_workspace_manager.py`.

## Layers

**Skill Contract Layer:**
- Purpose: define the public, human-readable workflow surface.
- Location: `skills/`
- Contains: stage skill docs, shared references, and workflow markdown such as `skills/rd-agent/workflows/intent-routing.md` and `skills/_shared/references/stage-contract.md`.
- Depends on: executable entrypoints in `v3/entry/` and shared policy text in `skills/_shared/references/`.
- Used by: agent runtimes after install, plus installer code in `v3/devtools/skill_install.py`.

**Entrypoint Layer:**
- Purpose: translate a skill invocation or CLI request into orchestrator calls and operator guidance.
- Location: `v3/entry/`
- Contains: `v3/entry/rd_agent.py`, `v3/entry/rd_propose.py`, `v3/entry/rd_code.py`, `v3/entry/rd_execute.py`, `v3/entry/rd_evaluate.py`, `v3/entry/tool_catalog.py`, and `v3/entry/tool_cli.py`.
- Depends on: `v3/tools/`, `v3/orchestration/`, `v3/contracts/`, and `v3/ports/`.
- Used by: skill packages in `skills/`, the console script `rdagent-v3-tool` from `pyproject.toml`, and tests such as `tests/test_phase29_entry_wiring.py`.

**Tool Adapter Layer:**
- Purpose: expose one-function, schema-validated operations that can be reused by both skills and the CLI.
- Location: `v3/tools/`
- Contains: read adapters like `v3/tools/run_tools.py`, `v3/tools/branch_tools.py`, `v3/tools/stage_tools.py`, and write/orchestration adapters like `v3/tools/stage_write_tools.py`, `v3/tools/orchestration_tools.py`, `v3/tools/exploration_tools.py`, and `v3/tools/finalization_tools.py`.
- Depends on: request/result models in `v3/contracts/tool_io.py` and concrete services in `v3/orchestration/`.
- Used by: `_TOOL_SPECS` in `v3/entry/tool_catalog.py` and the stage entry modules in `v3/entry/`.

**Orchestration Service Layer:**
- Purpose: implement all mutable runtime behavior.
- Location: `v3/orchestration/`
- Contains: run lifecycle services (`v3/orchestration/run_board_service.py`, `v3/orchestration/stage_transition_service.py`), single-branch flow (`v3/orchestration/skill_loop_service.py`), multi-branch flow (`v3/orchestration/multi_branch_service.py`), branch management (`v3/orchestration/branch_lifecycle_service.py`, `v3/orchestration/branch_board_service.py`, `v3/orchestration/selection_service.py`, `v3/orchestration/branch_prune_service.py`, `v3/orchestration/branch_merge_service.py`, `v3/orchestration/branch_share_service.py`), recovery/preflight (`v3/orchestration/recovery_service.py`, `v3/orchestration/preflight_service.py`, `v3/orchestration/resume_planner.py`), and DAG/finalization logic (`v3/orchestration/dag_service.py`, `v3/orchestration/select_parents_service.py`, `v3/orchestration/holdout_validation_service.py`).
- Depends on: `v3/contracts/`, `v3/ports/`, and pure helpers in `v3/algorithms/`.
- Used by: `v3/entry/` and `v3/tools/`.

**Contract Layer:**
- Purpose: lock the runtime vocabulary for run, branch, stage, memory, exploration, recovery, preflight, and tool payloads.
- Location: `v3/contracts/`
- Contains: immutable Pydantic models such as `RunBoardSnapshot`, `BranchSnapshot`, `StageSnapshot`, `OperatorGuidance`, `PreflightResult`, `FinalSubmissionSnapshot`, and the request/result classes in `v3/contracts/tool_io.py`.
- Depends on: other contract modules only.
- Used by: every layer above and below it.

**Port and Adapter Layer:**
- Purpose: keep persistence and external dependencies replaceable.
- Location: `v3/ports/` and concrete adapters in `v3/orchestration/`
- Contains: `v3/ports/state_store.py`, `v3/ports/memory_store.py`, `v3/ports/execution.py`, `v3/ports/holdout_port.py`, `v3/ports/embedding_port.py`, plus concrete adapters `v3/orchestration/artifact_state_store.py`, `v3/orchestration/memory_state_store.py`, and `v3/orchestration/branch_workspace_manager.py`.
- Depends on: contracts in `v3/contracts/`.
- Used by: orchestration services, especially `RunBoardService`, `RecoveryService`, `BranchShareService`, and `HoldoutValidationService`.

**Algorithm Layer:**
- Purpose: keep selection, pruning, DAG traversal, complementarity, and holdout math pure and testable.
- Location: `v3/algorithms/`
- Contains: `v3/algorithms/puct.py`, `v3/algorithms/prune.py`, `v3/algorithms/dag.py`, `v3/algorithms/holdout.py`, `v3/algorithms/complementarity.py`, `v3/algorithms/interaction_kernel.py`, `v3/algorithms/decay.py`, and `v3/algorithms/merge.py`.
- Depends on: Python stdlib plus some contract enums in a few modules.
- Used by: orchestration services such as `v3/orchestration/selection_service.py`, `v3/orchestration/branch_prune_service.py`, `v3/orchestration/dag_service.py`, and `v3/orchestration/branch_merge_service.py`.

**Compatibility Layer:**
- Purpose: isolate legacy V2 translation logic away from V3 core ownership.
- Location: `v3/compat/v2/`
- Contains: `v3/compat/v2/migration_reads.py` and `v3/compat/v2/translators.py`.
- Depends on: V3 contracts and ports only.
- Used by: `v3/orchestration/recovery_service.py` through optional migration/backfill hooks.

## Data Flow

**Primary Path - Start or continue through `rd-agent`:**

1. The operator-facing contract starts at `skills/rd-agent/SKILL.md`; `v3/entry/rd_agent.py` either routes intent with `route_user_intent` or runs `rd_agent`.
2. `v3/entry/rd_agent.py` starts a run through `call_cli_tool("rd_run_start", ...)`, which resolves into `v3/tools/run_tools.py` and `v3/orchestration/run_board_service.py`.
3. `RunBoardService.start_run` delegates the initial work unit to an injected `ExecutionPort` from `v3/ports/execution.py`, then persists the resulting run, branch, stage, and artifact snapshots through `StateStorePort` in `v3/ports/state_store.py`.
4. If the request is single-branch, `v3/orchestration/skill_loop_service.py` advances `StageKey.FRAMING -> BUILD -> VERIFY -> SYNTHESIZE` by calling `v3/entry/rd_propose.py`, `v3/entry/rd_code.py`, `v3/entry/rd_execute.py`, and `v3/entry/rd_evaluate.py`.
5. If the request is multi-branch, `v3/orchestration/multi_branch_service.py` forks branches through `v3/orchestration/branch_lifecycle_service.py`, allocates isolated workspaces through `v3/orchestration/branch_workspace_manager.py`, projects board state through `v3/orchestration/branch_board_service.py`, and optionally finalizes through `v3/orchestration/holdout_validation_service.py`.

**Auxiliary Path - Resume a known paused stage skill:**

1. `skills/rd-propose/SKILL.md`, `skills/rd-code/SKILL.md`, `skills/rd-execute/SKILL.md`, or `skills/rd-evaluate/SKILL.md` maps to the matching module in `v3/entry/`.
2. The stage entrypoint loads current truth through read tools such as `rd_run_get`, `rd_branch_get`, `rd_stage_get`, `rd_artifact_list`, and `rd_recovery_assess` from `v3/tools/`.
3. `v3/orchestration/preflight_service.py` determines executability, and `v3/orchestration/resume_planner.py` turns stage state plus recovery state into a `REUSE`, `REPLAY`, `REBUILD`, or `REVIEW` decision.
4. If the stage can advance, `v3/tools/stage_write_tools.py` publishes completion, replay, or blocking through `v3/orchestration/stage_transition_service.py`; otherwise the entrypoint returns structured operator guidance from `v3/orchestration/operator_guidance.py`.

**Auxiliary Path - Direct tool inspection or direct primitive call:**

1. The console script `rdagent-v3-tool` from `pyproject.toml` enters `v3/entry/tool_cli.py`.
2. `v3/entry/tool_cli.py` uses `list_cli_tools()` or `get_cli_tool()` from `v3/entry/tool_catalog.py`.
3. `v3/entry/tool_catalog.py` is the single registry for direct tools. `_TOOL_SPECS` binds schema, routing metadata, examples, and the actual handler in `v3/tools/`.
4. The selected tool handler validates the request model, calls an orchestration service, and returns both `structuredContent` and plain-text guidance. Tests in `tests/test_v3_tool_cli.py`, `tests/test_phase16_tool_surface.py`, and `tests/test_phase31_tools.py` lock this shape down.

**Auxiliary Path - Skill installation and runtime bundle creation:**

1. `scripts/install_agent_skills.py` parses `--runtime`, `--scope`, and `--mode`.
2. `v3/devtools/skill_install.py` discovers `skills/*/SKILL.md`, renders installed `SKILL.md` files, and materializes a runtime bundle rooted at `.codex/rdagent-v3`, `.claude/rdagent-v3`, `~/.codex/rdagent-v3`, or `~/.claude/rdagent-v3`.
3. The installer creates installed skill directories under `.codex/skills`, `.claude/skills`, `~/.codex/skills`, or `~/.claude/skills`, while preserving unmanaged directories.

**State Management:**
- Canonical run/branch/stage/artifact/decision/DAG/finalization state is stored as JSON under a root managed by `v3/orchestration/artifact_state_store.py`.
- Branch-local workspaces, artifact roots, memory roots, and shared memory roots are derived by `v3/orchestration/branch_isolation_service.py` and used by `v3/orchestration/branch_workspace_manager.py` and `v3/orchestration/memory_state_store.py`.

## Key Abstractions

**`RunBoardSnapshot`, `BranchSnapshot`, `StageSnapshot`:**
- Purpose: represent the top-level runtime state vocabulary.
- Examples: `v3/contracts/run.py`, `v3/contracts/branch.py`, `v3/contracts/stage.py`
- Pattern: immutable Pydantic snapshots passed across entrypoints, services, tools, and persistence.

**`StateStorePort` and `ArtifactStateStore`:**
- Purpose: separate persistence interface from the concrete JSON-on-filesystem implementation.
- Examples: `v3/ports/state_store.py`, `v3/orchestration/artifact_state_store.py`
- Pattern: port/adaptor boundary with write/read methods for run, branch, stage, artifact, decision, DAG, and final submission records.

**`_TOOL_SPECS` in `v3/entry/tool_catalog.py`:**
- Purpose: central registry for all direct tools and their schema metadata.
- Examples: `v3/entry/tool_catalog.py`, `tests/test_phase16_tool_surface.py`
- Pattern: metadata-driven dispatch table over typed request/response models.

**`SkillLoopService`:**
- Purpose: own the single-branch stage loop without exposing stage sequencing to callers.
- Examples: `v3/orchestration/skill_loop_service.py`, `tests/test_phase16_rd_agent.py`
- Pattern: stage-order orchestrator that delegates work to public stage entry modules and persists stop reasons on the run snapshot.

**`MultiBranchService`:**
- Purpose: coordinate fork/dispatch/share/prune/select/finalize behavior for multi-branch exploration.
- Examples: `v3/orchestration/multi_branch_service.py`, `tests/test_phase26_integration.py`, `tests/test_phase28_integration.py`, `tests/test_phase31_integration.py`
- Pattern: coordinator service that composes smaller services instead of putting all logic in the entry layer.

**`OperatorGuidance`:**
- Purpose: unify how entrypoints explain current state, routing reason, and exact next action.
- Examples: `v3/contracts/operator_guidance.py`, `v3/orchestration/operator_guidance.py`, `tests/test_phase24_operator_guidance.py`
- Pattern: shared response contract reused by `rd-agent` and all stage entrypoints.

**`DAGService` and `FinalSubmissionSnapshot`:**
- Purpose: separate exploration topology and final ranking from the branch lifecycle snapshot.
- Examples: `v3/orchestration/dag_service.py`, `v3/orchestration/holdout_validation_service.py`, `v3/contracts/exploration.py`
- Pattern: graph-backed exploration layer with frontier, ancestry, merge-edge, and holdout-finalization support.

## Entry Points

**Primary orchestration entrypoint:**
- Location: `skills/rd-agent/SKILL.md` and `v3/entry/rd_agent.py`
- Triggers: start a new run, continue a paused run, or route to a narrower surface.
- Responsibilities: intent routing, paused-run detection, service wiring, single-branch loop execution, multi-branch round execution, and final operator guidance.

**Stage continuation entrypoints:**
- Location: `skills/rd-propose/SKILL.md`, `skills/rd-code/SKILL.md`, `skills/rd-execute/SKILL.md`, `skills/rd-evaluate/SKILL.md` plus `v3/entry/rd_propose.py`, `v3/entry/rd_code.py`, `v3/entry/rd_execute.py`, `v3/entry/rd_evaluate.py`
- Triggers: continue an already-known paused branch stage.
- Responsibilities: load current state, run preflight, assess recovery, publish replay/completion/blocking, and hand back the next skill recommendation.

**Direct CLI catalog entrypoint:**
- Location: `v3/entry/tool_cli.py` and `v3/entry/tool_catalog.py`
- Triggers: `rdagent-v3-tool list` and `rdagent-v3-tool describe <tool>`
- Responsibilities: expose the direct-tool registry, render JSON for machine consumption, and keep the direct-tool surface transport-free.

**Installer entrypoint:**
- Location: `scripts/install_agent_skills.py`
- Triggers: repo-local install commands described in `README.md`
- Responsibilities: wrap `v3/devtools/skill_install.py` for local/global Claude and Codex installation.

**Verification entrypoints:**
- Location: `Makefile` and `.github/workflows/ci.yml`
- Triggers: local `make lint`, `make test`, `make verify`, and CI on push/pull request.
- Responsibilities: lint `v3/`, `tests/`, `scripts/`, run pytest, and enforce the public-surface contracts.

## Error Handling

**Strategy:** Fail fast on invalid state or invalid wiring, but encode operator-visible blockage as typed preflight and guidance payloads instead of silent fallback behavior.

**Patterns:**
- Lookup and ownership violations raise hard errors such as `KeyError` and `ValueError` in `v3/orchestration/run_board_service.py`, `v3/orchestration/stage_transition_service.py`, `v3/orchestration/branch_lifecycle_service.py`, and all stage entry modules in `v3/entry/`.
- `v3/orchestration/preflight_service.py` converts environment/state/artifact/recovery problems into a typed `PreflightResult`, which stage entrypoints surface as `preflight_blocked` outcomes instead of guessing.
- `v3/orchestration/recovery_service.py` and `v3/orchestration/resume_planner.py` distinguish `REUSE`, `REPLAY`, `REBUILD`, and `REVIEW` so the system does not hide missing evidence behind optimistic continuation.
- Graph and path safety checks are explicit: `v3/orchestration/dag_service.py` rejects invalid parents and cycles, while `v3/orchestration/branch_isolation_service.py` rejects path traversal or root escape.

## Cross-Cutting Concerns

**Logging:** No dedicated logging subsystem is the main architectural path. The public surfaces prefer structured JSON payloads plus concise human-readable text from `v3/tools/` and `v3/entry/tool_cli.py`; tests such as `tests/test_v3_tool_cli.py` and `tests/test_phase24_operator_guidance.py` treat those payloads as the observable contract.

**Validation:** Validation is layered. `v3/contracts/*.py` and `v3/contracts/tool_io.py` enforce schema correctness, `v3/orchestration/preflight_service.py` enforces runtime/dependency/state truth, and `tests/test_phase23_preflight_service.py`, `tests/test_phase20_stage_skill_contracts.py`, and `tests/test_phase26_contracts.py` lock the contract surface.

**Authentication:** Not applicable. No auth provider, token middleware, or user identity boundary is implemented in `v3/`; the runtime assumes local, repo-scoped execution.

---

*Architecture analysis: 2026-03-25*
