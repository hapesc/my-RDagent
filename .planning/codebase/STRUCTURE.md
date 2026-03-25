# Codebase Structure

**Analysis Date:** 2026-03-25

## Directory Layout

```text
my-RDagent-V3/
├── README.md                      # public narrative: setup, routing, and operator usage
├── pyproject.toml                 # package metadata, pytest config, and `rdagent-v3-tool`
├── Makefile                       # local lint/test/verify shortcuts
├── .github/workflows/ci.yml       # CI matrix for lint + pytest
├── scripts/                       # repo-local helper CLIs and setup scripts
├── skills/                        # canonical skill packages consumed by agent runtimes
├── v3/                            # Python implementation of the standalone runtime
│   ├── entry/                     # public skill and CLI entrypoints
│   ├── orchestration/             # lifecycle, recovery, selection, DAG, and finalization services
│   ├── tools/                     # thin request/response adapters over services
│   ├── contracts/                 # immutable Pydantic contracts
│   ├── ports/                     # replaceable external seams
│   ├── algorithms/                # pure selection/pruning/merge/holdout helpers
│   ├── compat/v2/                 # explicit legacy translation seam
│   └── devtools/                  # installation support code
├── tests/                         # regression suites for contracts, wiring, and integration flows
├── .planning/                     # committed project planning and codebase mapping docs
├── .claude/                       # local Claude install target created by installer flows
└── .codex/                        # local Codex install target created by installer flows
```

## Directory Purposes

**`scripts/`:**
- Purpose: expose repo-local helper commands without widening the published console-script surface.
- Contains: `scripts/install_agent_skills.py`, `scripts/setup_env.sh`, and `scripts/bump_version.py`.
- Key files: `scripts/install_agent_skills.py`, `scripts/setup_env.sh`

**`skills/`:**
- Purpose: store the canonical agent-facing workflow surface.
- Contains: one directory per skill plus shared reference material in `skills/_shared/references/`.
- Key files: `skills/rd-agent/SKILL.md`, `skills/rd-propose/SKILL.md`, `skills/rd-code/SKILL.md`, `skills/rd-execute/SKILL.md`, `skills/rd-evaluate/SKILL.md`, `skills/rd-tool-catalog/SKILL.md`

**`v3/entry/`:**
- Purpose: hold the executable boundary for skill invocation and CLI inspection.
- Contains: orchestration entrypoints (`v3/entry/rd_agent.py`, `v3/entry/rd_propose.py`, `v3/entry/rd_code.py`, `v3/entry/rd_execute.py`, `v3/entry/rd_evaluate.py`) and direct-tool entrypoints (`v3/entry/tool_catalog.py`, `v3/entry/tool_cli.py`).
- Key files: `v3/entry/rd_agent.py`, `v3/entry/tool_catalog.py`, `v3/entry/tool_cli.py`

**`v3/orchestration/`:**
- Purpose: implement all nontrivial runtime behavior.
- Contains: persistence adapters (`v3/orchestration/artifact_state_store.py`, `v3/orchestration/memory_state_store.py`), lifecycle services (`v3/orchestration/run_board_service.py`, `v3/orchestration/stage_transition_service.py`), branch services (`v3/orchestration/branch_lifecycle_service.py`, `v3/orchestration/branch_board_service.py`, `v3/orchestration/selection_service.py`, `v3/orchestration/branch_prune_service.py`, `v3/orchestration/branch_merge_service.py`, `v3/orchestration/branch_share_service.py`), stage utilities (`v3/orchestration/recovery_service.py`, `v3/orchestration/preflight_service.py`, `v3/orchestration/resume_planner.py`), and topology/finalization services (`v3/orchestration/dag_service.py`, `v3/orchestration/select_parents_service.py`, `v3/orchestration/holdout_validation_service.py`, `v3/orchestration/multi_branch_service.py`).
- Key files: `v3/orchestration/skill_loop_service.py`, `v3/orchestration/multi_branch_service.py`, `v3/orchestration/preflight_service.py`, `v3/orchestration/holdout_validation_service.py`

**`v3/tools/`:**
- Purpose: provide small handler functions that expose orchestration services through a consistent response envelope.
- Contains: read tools (`v3/tools/run_tools.py`, `v3/tools/branch_tools.py`, `v3/tools/stage_tools.py`, `v3/tools/artifact_tools.py`, `v3/tools/recovery_tools.py`), mutation tools (`v3/tools/stage_write_tools.py`, `v3/tools/exploration_tools.py`, `v3/tools/memory_tools.py`, `v3/tools/finalization_tools.py`), and orchestration tools (`v3/tools/orchestration_tools.py`).
- Key files: `v3/tools/stage_write_tools.py`, `v3/tools/orchestration_tools.py`, `v3/tools/finalization_tools.py`

**`v3/contracts/`:**
- Purpose: define the public schema for all runtime state and tool payloads.
- Contains: snapshot models in `v3/contracts/run.py`, `v3/contracts/branch.py`, `v3/contracts/stage.py`, `v3/contracts/artifact.py`, `v3/contracts/exploration.py`, `v3/contracts/memory.py`, `v3/contracts/recovery.py`, `v3/contracts/preflight.py`, `v3/contracts/operator_guidance.py`, `v3/contracts/isolation.py`, plus request/result models in `v3/contracts/tool_io.py`.
- Key files: `v3/contracts/tool_io.py`, `v3/contracts/exploration.py`, `v3/contracts/preflight.py`

**`v3/ports/`:**
- Purpose: define replaceable seams for persistence and external capabilities.
- Contains: `v3/ports/state_store.py`, `v3/ports/memory_store.py`, `v3/ports/execution.py`, `v3/ports/holdout_port.py`, `v3/ports/embedding_port.py`, `v3/ports/recovery.py`, and `v3/ports/migration.py`.
- Key files: `v3/ports/state_store.py`, `v3/ports/execution.py`, `v3/ports/holdout_port.py`

**`v3/algorithms/`:**
- Purpose: isolate pure selection, pruning, DAG, merge, interaction-kernel, and holdout math from service wiring.
- Contains: `v3/algorithms/puct.py`, `v3/algorithms/prune.py`, `v3/algorithms/dag.py`, `v3/algorithms/holdout.py`, `v3/algorithms/complementarity.py`, `v3/algorithms/interaction_kernel.py`, `v3/algorithms/decay.py`, `v3/algorithms/merge.py`.
- Key files: `v3/algorithms/puct.py`, `v3/algorithms/prune.py`, `v3/algorithms/holdout.py`

**`v3/compat/v2/`:**
- Purpose: quarantine legacy V2 translation logic away from current V3 ownership.
- Contains: `v3/compat/v2/migration_reads.py` and `v3/compat/v2/translators.py`.
- Key files: `v3/compat/v2/translators.py`, `v3/compat/v2/migration_reads.py`

**`v3/devtools/`:**
- Purpose: support local/global installation and generated-skill rendering.
- Contains: `v3/devtools/skill_install.py`.
- Key files: `v3/devtools/skill_install.py`

**`tests/`:**
- Purpose: lock the public surface, orchestration behavior, and integration wiring.
- Contains: tool/CLI tests (`tests/test_v3_tool_cli.py`, `tests/test_phase16_tool_surface.py`, `tests/test_phase31_tools.py`), skill contract tests (`tests/test_phase20_rd_agent_skill_contract.py`, `tests/test_phase20_stage_skill_contracts.py`), preflight/operator guidance tests (`tests/test_phase23_preflight_service.py`, `tests/test_phase24_operator_guidance.py`), and integration suites across later phases (`tests/test_phase26_integration.py`, `tests/test_phase27_integration.py`, `tests/test_phase28_integration.py`, `tests/test_phase29_entry_wiring.py`, `tests/test_phase31_integration.py`).
- Key files: `tests/test_v3_tool_cli.py`, `tests/test_phase29_entry_wiring.py`, `tests/test_phase31_integration.py`

**`.planning/`:**
- Purpose: keep committed project state, milestone history, validation notes, and mapper outputs together.
- Contains: `.planning/STATE.md`, `.planning/PROJECT.md`, `.planning/ROADMAP.md`, milestone docs under `.planning/milestones/`, phase docs under `.planning/phases/`, and these mapping files under `.planning/codebase/`.
- Key files: `.planning/STATE.md`, `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`

## Key File Locations

**Entry Points:**
- `skills/rd-agent/SKILL.md`: top-level operator contract for start/continue routing
- `skills/rd-tool-catalog/SKILL.md`: operator contract for narrowing to direct tools
- `v3/entry/rd_agent.py`: main runtime entrypoint and intent router
- `v3/entry/rd_propose.py`: framing-stage continuation entrypoint
- `v3/entry/rd_code.py`: build-stage continuation entrypoint
- `v3/entry/rd_execute.py`: verify-stage continuation entrypoint
- `v3/entry/rd_evaluate.py`: synthesize-stage continuation entrypoint
- `v3/entry/tool_cli.py`: implementation behind `rdagent-v3-tool`

**Configuration:**
- `pyproject.toml`: package metadata, Python requirement, optional test/lint dependencies, pytest settings, and the `rdagent-v3-tool` script
- `Makefile`: local `test`, `lint`, `format`, `verify`, and install shortcuts
- `.github/workflows/ci.yml`: CI matrix that runs `uv sync --extra test --extra lint`, `make lint`, and `make test`

**Core Logic:**
- `v3/orchestration/skill_loop_service.py`: single-branch stage sequencing
- `v3/orchestration/multi_branch_service.py`: multi-branch exploration and finalization coordinator
- `v3/orchestration/run_board_service.py`: run start/publication service
- `v3/orchestration/stage_transition_service.py`: stage snapshot publisher
- `v3/orchestration/preflight_service.py`: runtime/state/dependency gate
- `v3/orchestration/recovery_service.py`: reuse/replay/rebuild assessment
- `v3/orchestration/dag_service.py`: exploration graph topology
- `v3/orchestration/holdout_validation_service.py`: final holdout ranking

**Testing:**
- `tests/test_v3_tool_cli.py`: `list` and `describe` CLI contract
- `tests/test_phase16_rd_agent.py`: baseline multi-branch orchestration expectations
- `tests/test_phase20_rd_agent_skill_contract.py`: `rd-agent` skill doc contract
- `tests/test_phase20_stage_skill_contracts.py`: stage-skill doc contracts
- `tests/test_phase23_preflight_service.py`: preflight blocker behavior
- `tests/test_phase24_operator_guidance.py`: operator-guidance text and routing shape
- `tests/test_phase29_entry_wiring.py`: entry-layer wiring for sharing/finalization
- `tests/test_phase31_integration.py`: graceful degradation and finalization state integration

## Naming Conventions

**Files:**
- Python implementation files use `snake_case.py`, for example `v3/entry/rd_agent.py` and `v3/orchestration/branch_merge_service.py`.
- Skill roots use hyphenated directory names with a required `SKILL.md`, for example `skills/rd-agent/SKILL.md` and `skills/rd-tool-catalog/SKILL.md`.
- Tests use `tests/test_*.py`; many suites also carry a phase prefix such as `tests/test_phase23_preflight_service.py` or `tests/test_phase31_tools.py`.

**Directories:**
- Runtime packages are grouped by architectural role under `v3/entry/`, `v3/orchestration/`, `v3/tools/`, `v3/contracts/`, `v3/ports/`, `v3/algorithms/`, `v3/compat/`, and `v3/devtools/`.
- Skill package directories under `skills/` match their public command names, for example `skills/rd-code/` and `skills/rd-evaluate/`.

## Where to Add New Code

**New Feature:**
- Primary code: start from `v3/contracts/` for the data model, add or extend service logic in `v3/orchestration/`, expose it through `v3/tools/`, and wire it into `v3/entry/` only if it changes the public surface.
- Tests: add focused coverage in `tests/` near the affected layer; use `tests/test_v3_tool_cli.py` for CLI shape changes, `tests/test_phase20_*` for skill-doc contract changes, and the highest relevant integration phase file for end-to-end behavior.

**New Component/Module:**
- Implementation: pure algorithms belong in `v3/algorithms/`; stateful services belong in `v3/orchestration/`; new replaceable interfaces belong in `v3/ports/`; legacy translation belongs only in `v3/compat/v2/`.
- Public entry wiring: add a new skill doc under `skills/<name>/` only when the feature is a human-facing surface. Add a direct tool by updating `v3/contracts/tool_io.py`, the relevant `v3/tools/*.py` module, and `_TOOL_SPECS` in `v3/entry/tool_catalog.py`.

**Utilities:**
- Shared helpers: keep repo-level helper scripts in `scripts/` and installation helpers in `v3/devtools/`.
- Shared documentation fragments: put reusable skill text in `skills/_shared/references/`, not duplicated across `skills/rd-*/SKILL.md`.

## Special Directories

**`.planning/`:**
- Purpose: committed planning state and historical phase artifacts
- Generated: No
- Committed: Yes

**`.claude/`:**
- Purpose: local Claude runtime/skill install target used by `scripts/install_agent_skills.py`
- Generated: Yes
- Committed: No

**`.codex/`:**
- Purpose: local Codex runtime/skill install target used by `scripts/install_agent_skills.py`
- Generated: Yes
- Committed: No

**`v3/compat/v2/`:**
- Purpose: explicit legacy translation seam; keep non-V3 vocabulary here instead of mixing it into `v3/orchestration/`
- Generated: No
- Committed: Yes

**`skills/_shared/references/`:**
- Purpose: shared workflow/reference fragments reused by multiple skill packages
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-03-25*
