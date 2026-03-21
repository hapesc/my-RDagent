# Codebase Structure

**Analysis Date:** 2026-03-21

## Directory Layout

```
my-RDagent-V3/
├── README.md                     # public surface, setup, and routing guidance
├── pyproject.toml                # packaging, dependencies, and `rdagent-v3-tool` script
├── uv.lock                       # `uv sync --extra test` lockfile mentioned in README
├── scripts/                      # repo-local helpers (installer wrapper)
│   └── install_agent_skills.py    # installer CLI exposing --runtime/--scope/--mode
├── skills/                       # canonical skill packages with SKILL.md docs
│   ├── rd-agent/SKILL.md          # default orchestration skill
│   ├── rd-propose/SKILL.md        # framing-stage skill
│   ├── rd-code/SKILL.md           # build-stage skill
│   ├── rd-execute/SKILL.md        # verify-stage skill
│   ├── rd-evaluate/SKILL.md       # synthesize-stage skill
│   └── rd-tool-catalog/SKILL.md   # CLI catalog decision helper
├── v3/                           # Python implementation packages
│   ├── entry/                    # skill+CLI entrypoints documented above
│   ├── orchestration/            # services that manage runs, branches, and transitions
│   ├── contracts/                # Pydantic snapshots used everywhere
│   ├── tools/                    # thin helpers referenced by `v3.entry.tool_catalog`
│   ├── ports/                    # persistence interfaces such as `StateStorePort`
│   ├── devtools/                 # install/link helper logic like `skill_install.py`
│   └── compat/                   # legacy helpers under `compat/v2`
├── tests/                        # regression suites gating docs and installer behavior
│   ├── test_v3_tool_cli.py        # CLI contract
│   ├── test_phase16_rd_agent.py   # orchestration and branch/run behavior
│   ├── test_phase18_skill_installation.py  # installer coverage
│   └── test_phase18_planning_continuity.py # README/.planning continuity checks
└── .planning/                    # planning artifacts, state, and codebase docs
    ├── STATE.md                 # canonical continuity entrypoint
    ├── phases/                  # phase-specific plans, research, validation
    ├── PROJECT.md               # milestone context and constraints
    └── codebase/                 # mapping docs (ARCHITECTURE.md, STRUCTURE.md)
```

## Directory Purposes

**`.planning/`:**
- Purpose: host planning artifacts, continuity state, and mapping deliverables.
- Contains: `.planning/STATE.md` as current phase status, `.planning/phases/18-standalone-packaging-and-planning-autonomy/18-RESEARCH.md` (phase decisions), `.planning/V3-EXTRACTION-HANDOFF.md` (historical archive), and the `codebase` folder where these analysis docs live.
- Key files: `.planning/STATE.md`, `.planning/phases/18-standalone-packaging-and-planning-autonomy/18-RESEARCH.md`, `.planning/phases/.../18-VALIDATION.md` for regression definitions.

**`scripts/`:**
- Purpose: repo-local utilities that keep the public CLI surface flat.
- Contains: `scripts/install_agent_skills.py`, the sole helper that parses `--runtime`, `--scope`, and `--mode` and delegates to `v3.devtools.skill_install.install_agent_skills`.
- Key files: `scripts/install_agent_skills.py` prints structured install records per the README example lines 39-66.

**`skills/`:**
- Purpose: each directory under `skills/` documents a readable skill contract and maps to a `v3.entry` module.
- Contains: `SKILL.md` files for `rd-agent`, `rd-propose`, `rd-code`, `rd-execute`, `rd-evaluate`, and `rd-tool-catalog`; these docs define routing advice (when to route to `rd-tool-catalog`, when not to use the skill).
- Key files: `skills/rd-agent/SKILL.md` (default loop entry), `skills/rd-tool-catalog/SKILL.md` (decision helper for primitives).

**`v3/`:**
- Purpose: implementation packages for orchestrator entrypoints, services, contracts, tools, and dev utilities.
- Contains: `v3/entry` (e.g., `rd_agent.py`, `tool_catalog.py`), `v3/orchestration` services (`skill_loop_service.py`, `branch_*` services, `stage_transition_service.py`), `v3/tools` helpers (wrappers for `rd_stage_complete`, artifact queries, memory helpers), `v3/contracts` (typed request/response models), `v3/ports` (e.g., `state_store.py`, `recovery.py`, `execution.py`), `v3/devtools/skill_install.py`, and `v3/compat/v2` for legacy migrations.
- Key files: `v3/entry/rd_agent.py`, `v3/orchestration/skill_loop_service.py`, `v3/entry/tool_catalog.py`, `v3/devtools/skill_install.py`, `v3/ports/state_store.py`.

**`tests/`:**
- Purpose: regression suites that guard CLI tooling, orchestration decisions, installer behavior, and planning continuity.
- Contains: stage and tool guards (`tests/test_phase16_rd_agent.py`, `tests/test_v3_tool_cli.py`), installer robustness (`tests/test_phase18_skill_installation.py`), and doc/STATE gating (`tests/test_phase18_planning_continuity.py`).
- Key files: `tests/test_phase18_skill_installation.py`, `tests/test_phase18_planning_continuity.py` ensure README and continuity documents follow Phase 18 conventions printed in README lines 157-170.

## Key File Locations

- `README.md`: public onboarding, repo setup, `uv run` commands, skill installer instructions (lines 3-170).
- `pyproject.toml`: package metadata, dependency list (`pydantic`, `pytest`, `import-linter`), and the single console script `rdagent-v3-tool` pointing to `v3.entry.tool_cli:main`.
- `scripts/install_agent_skills.py`: repo-local wrapper described above (lines 17-66) that prints runtime/scope/mode actions and fails with non-zero exit on exceptions.
- `v3/entry/rd_agent.py`: default orchestration entrypoint used by `skills/rd-agent/SKILL.md`, combining multi-branch exploration (`MultiBranchService`) and single-branch skill looping (`SkillLoopService`).
- `v3/orchestration/skill_loop_service.py`: sequences stage entrypoints and enforces `AgentExecutionPolicy` stages defined in `StageKey` order.
- `v3/entry/tool_catalog.py`: defines `_ToolSpec` metadata for each CLI primitive, used by `rdagent-v3-tool` (`v3/entry/tool_cli.py`).
- `v3/devtools/skill_install.py`: implements `discover_repo_root`, `resolve_target_root`, and `install_agent_skills` plus `InstallRecord` surfaced in installer tests.
- `.planning/STATE.md`: canonical continuity entrypoint (per `tests/test_phase18_planning_continuity.py`).
- `.planning/phases/18-standalone-packaging-and-planning-autonomy/18-RESEARCH.md`: documents Phase 18 constraints and patterns used for architecture decisions.
- `tests/test_phase18_skill_installation.py`: verifies installer link/copy behavior, broken-link repair, and preservation of unmanaged directories.
- `tests/test_phase18_planning_continuity.py`: ensures README keeps only public guidance and `.planning/STATE.md` is the active entrypoint.

## Naming Conventions

- Skill descriptions live in `skills/<skill>/SKILL.md` with explicit `name`, `description`, and routing advice (e.g., `skills/rd-agent/SKILL.md` lines 1-52).
- Python modules under `v3/` use snake_case filenames (`v3/entry/rd_agent.py`, `v3/orchestration/skill_loop_service.py`, `v3/tools/stage_write_tools.py`).
- Tests follow `tests/test_*.py` naming, matching `pyproject.toml` test discovery rules (`python_files = "test_*.py"`).
- Public CLI script `rdagent-v3-tool` is registered once and maps to `v3.entry.tool_cli.main` per `[project.scripts]` in `pyproject.toml`.
- Installer wrapper flags follow README usage (`--runtime`, `--scope`, `--mode` in `scripts/install_agent_skills.py`).

## Where to Add New Code

- **New skills or entrypoints:** add a `skills/<skill>/SKILL.md` doc and mirror entrypoint in `v3/entry/<skill>.py`, then wire the skill into `v3.entry.tool_catalog` if it exposes CLI primitives.
- **New orchestration services:** place them in `v3/orchestration/` (e.g., `StageTransitionService`, `SkillLoopService`) and expose helpers via `v3/tools/*.py` for reuse by `_TOOL_SPECS`.
- **New helper contracts:** extend `v3/contracts/*.py` for request/result models, keeping them in sync with `tests/test_phase16_rd_agent.py` patterns.
- **New CLI helpers:** append `_ToolSpec` entries in `v3/entry/tool_catalog.py`, update `v3/entry/tool_cli.py` to parse new describe/list behaviors if needed, and strengthen `tests/test_v3_tool_cli.py` accordingly.
- **New developer tooling:** add utilities to `v3/devtools/` and wrap them in `scripts/` when a repo-local CLI is required (avoid adding to `[project.scripts]`).
- **Documentation and planning:** add continuity or planning updates under `.planning/phases/` and `.planning/STATE.md`, then lock regressions through `tests/test_phase18_planning_continuity.py` and `tests/test_phase18_skill_installation.py` as appropriate.

## Special Directories

- **`.planning/`:** central planning state, with `.planning/STATE.md` as the active entrypoint and `.planning/codebase/` housing these analysis docs.
- **`skills/`:** canonical skill packages; each skill must maintain its `SKILL.md` and route to `v3.entry` modules without referencing legacy MCP surfaces.
- **`v3/devtools/`:** dev-only helpers (e.g., `skill_install.py`) used by repository-local scripts, not exported as public console commands.
- **`tests/`:** gated regressions for CLI, planning continuity, and installer behavior; these suites define the quick/full verification commands documented in the README.

---

*Structure analysis: 2026-03-21*
