# Architecture

**Analysis Date:** 2026-03-21

## Pattern Overview

**Overall:** Stage-aware skill/CLI orchestrator that drives V3 runs through layered services and a catalog of structured primitives.

**Key Characteristics:**
- High-level skills (`skills/rd-agent`, `skills/rd-propose`, `skills/rd-code`, `skills/rd-execute`, `skills/rd-evaluate`) map 1:1 to `v3.entry` entrypoints and keep the default surface inside `rd-agent` before dropping to stage-specific helpers. These modules route through the CLI tool catalog (e.g., `v3.entry.rd_agent.rd_agent` calls `v3.entry.tool_catalog.call_cli_tool`).
- `v3.orchestration` services own branch/workspace lifecycle (`BranchWorkspaceManager`, `MultiBranchService`, `SkillLoopService`, `StageTransitionService`, `RecoveryService`), ensuring deterministic state updates are funneled through `StateStorePort` implementations (`v3.ports.state_store.StateStorePort`).
- A schema-driven tool catalog (`v3.entry.tool_catalog` and `_TOOL_SPECS`) exposes primitives such as `rd_run_start`, `rd_branch_fork`, and `rd_memory_create` with Pydantic request/response models defined in `v3.contracts`, enabling the CLI layer (`v3.entry.tool_cli`) to stay transport-free and deterministic while still matching stage contracts.

## Layers

**Entrypoint Layer:**
- `v3.entry/rd_agent.py`, `v3.entry/rd_propose.py`, `v3.entry/rd_code.py`, `v3.entry/rd_execute.py`, `v3.entry/rd_evaluate.py`, and `v3.entry/tool_catalog.py` each implement the orchestrator-facing surface documented by their skill packages under `skills/`. Each module gathers run/branch IDs, calls into `v3.tools` helpers, and publishes stage artifacts through services such as `StageTransitionService` (`v3/orchestration/stage_transition_service.py`).
- The public CLI script `rdagent-v3-tool` (`pyproject.toml` → `[project.scripts]` pointing at `v3.entry.tool_cli:main`) is a thin `argparse` wrapper over `v3.entry.tool_catalog` (`v3/entry/tool_cli.py`).
- Repository-local helpers like `scripts/install_agent_skills.py` route installer flags to `v3.devtools.skill_install.install_agent_skills`, keeping installer logic out of the published surface while still enabling agent runtime integration.

**Orchestration Layer:**
- `v3/orchestration/skill_loop_service.py` runs a single branch through `StageKey.FRAMING → BUILD → VERIFY → SYNTHESIZE`, calling the applicable stage entrypoint and stopping when `SkillLoopService` decisions (based on `AgentExecutionPolicy`) indicate completion or blocking.
- Multi-branch support lives in `v3/orchestration/multi_branch_service.py`, `BranchLifecycleService`, `ConvergenceService`, and `BranchBoardService`, which coordinate listings, convergence rounds, and workspace isolation during exploration (`v3.entry.rd_agent` uses `BranchWorkspaceManager` plus `MultiBranchService`).
- Mutable state writes flow through `RunBoardService`, `StageTransitionService`, `RecoveryService`, and `ArtifactStateStore` (e.g., `v3/orchestration/run_board_service.py`, `v3/orchestration/stage_transition_service.py`, `v3/ports/state_store.py`). These services talk only to `StateStorePort`, keeping persistence plug-and-play.

**Tool Layer:**
- `v3.tools.*` modules (`artifact_tools.py`, `branch_tools.py`, `stage_tools.py`, etc.) are the thin wrappers that translate Pydantic request objects (from `v3/contracts/tool_io.py`) into service calls. They provide the handlers referenced by `_TOOL_SPECS` in `v3.entry.tool_catalog` so both skills and the CLI reuse the same concrete primitives.
- `v3.entry.tool_catalog` defines `_ToolSpec` metadata for every CLI command, including `category`, `subcategory`, `recommended_entrypoint`, and `command` text for `rdagent-v3-tool describe`. The catalog is the single coordination point for tooling exposures.

**Contracts & Ports:**
- `v3.contracts.*` contains typed snapshots (`run.py`, `branch.py`, `stage.py`, `tool_io.py`) used across services and entrypoints to validate CLI payloads and persistence records.
- `v3.contracts.tool_io` exports request/result classes consumed by `_TOOL_SPECS`, ensuring each CLI primitive is schema-checked before it reaches service code.
- `StateStorePort` (`v3/ports/state_store.py`) defines the persistence interface for run, branch, stage, artifact, recovery, and memory snapshots. Concrete `ArtifactStateStore` implementations (`tests/test_phase16_rd_agent.py` references `ArtifactStateStore`) back the test suite.

**Devtools & Installation:**
- `v3/devtools/skill_install.py` discovers repo root skills, validates `runtime`, `scope`, and `mode`, and installs each skill either as a symlink or a copy while recording `InstallRecord` entries. `scripts/install_agent_skills.py` mirrors the CLI flags described in README, printing one line per installed skill and bailing with a non-zero exit code on exceptions.
- Target roots (`~/.codex/skills`, `~/.claude/skills`, `./.codex/skills`, `./.claude/skills`) are resolved via `resolve_target_root`, so repo-local content can be linked into agent runtimes without expanding the public CLI surface.

**Skill Surface & Planning:**
- Each skill under `skills/` is paired with a `SKILL.md` file describing triggers, routing, and success contracts (`skills/rd-agent/SKILL.md`, `skills/rd-tool-catalog/SKILL.md`). Planning artifacts under `.planning/` (`STATE.md`, `phases/...`) capture roadmap decisions and validation scripts (`tests/test_phase18_planning_continuity.py`).

## Data Flow

1. A caller triggers the `rd-agent` skill (per `skills/rd-agent/SKILL.md`) or the `rdagent-v3-tool` CLI (`pyproject.toml` → `v3.entry.tool_cli.main`). `v3.entry.rd_agent` starts by invoking `call_cli_tool("rd_run_start", {...}, service=run_service)` to publish the initial run through `RunBoardService` (`v3/orchestration/run_board_service.py`).
2. `StateStorePort` writes the run snapshot, after which `SkillLoopService.run_single_branch` sequences stage inputs (`v3/orchestration/skill_loop_service.py`: iterate `StageKey` order, call stage-specific `rd_*` entrypoints, append history, evaluate `AgentExecutionPolicy`).
3. Each stage entrypoint (`v3.entry.rd_propose`, `v3.entry.rd_code`, `v3.entry.rd_execute`, `v3.entry.rd_evaluate`) loads branch/run/state data via `rd_branch_get`, `rd_stage_get`, `rd_artifact_list`, and `RecoveryService`, then publishes transitions through `StageTransitionService` or `rd_stage_complete`/`rd_stage_block` helpers (`v3/tools/stage_write_tools.py`).
4. Multi-branch mode creates workspaces via `BranchWorkspaceManager`, dispatches `ExploreRoundRequest` and `ConvergeRoundRequest` through `MultiBranchService`, and surfaces the board/merge summary to the caller along with recommendations (`v3.entry.rd_agent` handles both single-branch `SkillLoopService` results and multi-branch `MultiBranchService` outcomes).
5. When a caller needs direct primitives, `v3.entry.tool_cli` resolves `--command` arguments into `_ToolSpec`s from `v3.entry.tool_catalog`, which in turn call into `v3.tools.*` helpers (e.g., `rd_branch_fork`, `rd_memory_create`) that update services via contracts while leaving the CLI surface stateless.
6. Repo-local installation flows (`scripts/install_agent_skills.py` → `v3.devtools.skill_install.install_agent_skills`) enumerate `skills/*/SKILL.md`, resolve each runtime/scope target directory, and materialize either symlinks or copies for Claude/Codex roots documented in README.

## Key Abstractions

**`StateStorePort` (`v3/ports/state_store.py`):** Persistence port for run, branch, stage, artifact, recovery, and memory snapshots. Services only depend on this Protocol, making it easy to swap storage backends or mock them in `tests/test_phase16_rd_agent.py`.

**`RunBoardService` & `StageTransitionService` (`v3/orchestration/run_board_service.py`, `v3/orchestration/stage_transition_service.py`):** Publish run/branch truth and manage stage status updates while writing to the `StateStorePort`.

**`SkillLoopService` (`v3/orchestration/skill_loop_service.py`):** Choreographs framing/build/verify/synthesize stage entrypoints, enforces `AgentExecutionPolicy`, and persists stop reasons via `self._persist_run_stop`.

**Tool Catalog `_ToolSpec` (`v3/entry/tool_catalog.py`):** Metadata-driven dispatcher for CLI primitives with `category`, `subcategory`, and `recommended_entrypoint`, ensuring stage-aware tooling remains centralized.

**`InstallRecord` & installer helpers (`v3/devtools/skill_install.py`):** Represent each runtime/scope skill install action, track `action` strings (`linked`, `copied`, `preserved`), and allow tests (`tests/test_phase18_skill_installation.py`) to assert symlink vs copy behavior.

## Entry Points

**`rd-agent` skill:** Defined by `skills/rd-agent/SKILL.md` and implemented by `v3.entry.rd_agent.rd_agent`. It is the default orchestration surface, starts runs through `rd_run_start`, routes between multi-branch and single-branch paths, and relies on `SkillLoopService` plus `MultiBranchService` when `branch_hypotheses` are provided.

**Stage skills (`rd-propose`, `rd-code`, `rd-execute`, `rd-evaluate`):** Each has a `SKILL.md` file under `skills/<skill>/SKILL.md`, maps to `v3.entry.rd_<stage>.<function>`, and is used when callers know they need a specific stage. They validate that `run_id` and `branch_id` match and publish transitions through `StageTransitionService` helpers.

**`rd-tool-catalog`:** `skills/rd-tool-catalog/SKILL.md` points to `v3.entry.tool_catalog`, which enumerates CLI primitives and guides callers to either stay in `rd-agent` or drop to a primitive based on `_TOOL_SPECS` metadata.

**CLI entrypoint `rdagent-v3-tool`:** `pyproject.toml` exposes `v3.entry.tool_cli:main`, which parses `list`/`describe` commands, uses `list_cli_tools`/`get_cli_tool`, renders JSON, and exits with structured payloads documented in README.

**Installer script:** `scripts/install_agent_skills.py` is the repo-local entrypoint for `v3.devtools.skill_install.install_agent_skills`, exposing `--runtime`, `--scope`, and `--mode` flags exactly as documented in README without becoming a second public console script.

## Error Handling

- `v3.entry.rd_agent` raises `KeyError` when the run snapshot cannot be loaded after `rd_run_start`, ensuring callers know that persistence failed (`v3.entry/rd_agent.py` lines 53-62).
- Each stage entrypoint checks branch/run alignment (`v3.entry/rd_propose.py` lines 52-57) and raises `ValueError` if the branch belongs to another run, preventing stage leakage.
- `_expand_selection`, `resolve_target_root`, and `install_agent_skills` in `v3.devtools/skill_install.py` raise `ValueError` for unsupported runtimes/scopes/modes, and the installer script wraps calls in a try/except that prints failures and exits non-zero (`scripts/install_agent_skills.py` lines 42-66).
- `StageTransitionService` guards branch lookups and stage ordering, raising `KeyError` when a branch is missing (`v3/orchestration/stage_transition_service.py` lines 45-69).

## Cross-Cutting Concerns

**Validation:** Every CLI primitive uses Pydantic request/result models from `v3.contracts.tool_io` (`v3.entry.tool_catalog`), guaranteeing strict schema validation before any service call. Tests such as `tests/test_phase16_rd_agent.py` instantiate `RunStartRequest` and stage snapshots to prove the contracts move through the services.

**Observability:** CLI entrypoints and installer scripts emit structured text (JSON for `rdagent-v3-tool`, lines per installation for `scripts/install_agent_skills.py`) so callers can capture stable payloads.

**State truth:** `.planning/STATE.md`, `.planning/phases/18-standalone-packaging-and-planning-autonomy/18-RESEARCH.md`, and `tests/test_phase18_planning_continuity.py` enforce that README keeps only the public surface while `.planning/STATE.md` remains the canonical continuity entrypoint.

**Packaging compliance:** `pyproject.toml` restricts `[project.scripts]` to `rdagent-v3-tool` and lists dependencies (`pydantic`, `pytest`, `import-linter`) that match ACL requirements, while `uv.lock` pins transitive sets for `uv sync --extra test` as the README prescribes.

---

*Architecture analysis: 2026-03-21*
