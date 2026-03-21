# my-RDagent-V3

Standalone V3 extraction from `my-RDagent`, focused on the clean-split
agent-facing architecture rather than the legacy V1/V2 runtime shell.

## What This Repo Ships

This repository ships a standalone V3 surface made of skills plus CLI tools:

- repo-local skills under `skills/`
- V3 entrypoints under `v3.entry`
- a CLI-described tool catalog through `rdagent-v3-tool`
- focused tests that lock the public surface and the underlying contracts

The public surface is intentionally transport-free. It is not documented as a
server product. Instead, the repo exposes high-level skills first and direct
CLI tools second.

## Install

```bash
uv venv
uv sync --extra test
```

## Default Orchestration

Use `rd-agent` as the default orchestration entrypoint.

- Skill package: `skills/rd-agent/SKILL.md`
- Python entrypoint: `v3.entry.rd_agent.rd_agent`
- Purpose: start or continue the standalone V3 loop across single-branch and
  multi-branch execution

`rd-agent` is the default orchestration path because it keeps the high-level
run, branch, and stage flow inside V3-owned orchestration instead of forcing
the caller to choose direct primitives up front.

## Stage Skills

When the caller already knows it is working inside one owned stage, use the
stage-specific skills in this order:

1. `rd-propose`
   - Skill package: `skills/rd-propose/SKILL.md`
   - Python entrypoint: `v3.entry.rd_propose.rd_propose`
   - Role: framing stage, including reuse/review/replay logic before build
2. `rd-code`
   - Skill package: `skills/rd-code/SKILL.md`
   - Python entrypoint: `v3.entry.rd_code.rd_code`
   - Role: build stage before verify
3. `rd-execute`
   - Skill package: `skills/rd-execute/SKILL.md`
   - Python entrypoint: `v3.entry.rd_execute.rd_execute`
   - Role: verify stage, including blocked vs completed outcomes
4. `rd-evaluate`
   - Skill package: `skills/rd-evaluate/SKILL.md`
   - Python entrypoint: `v3.entry.rd_evaluate.rd_evaluate`
   - Role: synthesize stage, including continue vs stop recommendation

These stage skills are narrower than `rd-agent`. Use them when the branch
already has a known stage boundary and the caller does not need the default
end-to-end orchestration path.

## CLI Tool Catalog

Use `rd-tool-catalog` as the selective downshift layer when a high-level skill
boundary is insufficient and you need one direct CLI tool.

- Skill package: `skills/rd-tool-catalog/SKILL.md`
- Catalog module: `v3.entry.tool_catalog`
- CLI entrypoint: `rdagent-v3-tool`

List the available V3 CLI tools:

```bash
rdagent-v3-tool list
```

Describe one tool and inspect its schemas:

```bash
rdagent-v3-tool describe rd_run_start
rdagent-v3-tool describe rd_explore_round
```

The tool catalog emits stable machine-readable metadata for:

- `category`
- `subcategory`
- `recommended_entrypoint`

The top-level categories are:

- `orchestration`
- `inspection`
- `primitives`

Primitive tools are further narrowed by stable subcategories such as
`branch_lifecycle`, `branch_knowledge`, `branch_selection`, and `memory`.

## Routing Model

Use the public surface in this order:

1. Stay in `rd-agent` unless the task already belongs to one owned stage.
2. Use `rd-propose`, `rd-code`, `rd-execute`, or `rd-evaluate` when the caller
   is intentionally working inside that stage.
3. Drop to `rd-tool-catalog` only when a high-level skill is insufficient.
4. Inside `rd-tool-catalog`, narrow by `category` first, then by primitive
   `subcategory`, before selecting one direct tool.

This keeps high-level orchestration above direct primitives while still making
the CLI tool surface discoverable and explicit.

## Skill Authoring

New or refactored public skills in this repository should go through
`$skill-architect` first.

That keeps the repo-local `skills/*/SKILL.md` packages aligned with the actual
entrypoint modules and avoids drifting into a second, docs-only product
surface.

## Verification

Phase 17 public-surface checks:

```bash
uv run python -m pytest \
  tests/test_v3_tool_cli.py \
  tests/test_phase16_tool_surface.py \
  tests/test_phase17_surface_convergence.py \
  -q
```

Focused extraction smoke tests:

```bash
uv run python -m pytest \
  tests/test_v3_tool_cli.py \
  tests/test_phase14_skill_agent.py \
  tests/test_phase16_rd_agent.py \
  tests/test_phase16_tool_surface.py \
  -q
```

Boundary checks:

```bash
uv run lint-imports
```

Broader V3 regression set:

```bash
uv run python -m pytest \
  tests/test_phase13_v3_tools.py \
  tests/test_phase14_execution_policy.py \
  tests/test_phase14_resume_and_reuse.py \
  tests/test_phase14_stage_skills.py \
  tests/test_phase15_memory_contracts.py \
  tests/test_phase15_memory_retrieval.py \
  tests/test_phase15_branch_isolation.py \
  tests/test_phase16_branch_lifecycle.py \
  tests/test_phase16_convergence.py \
  tests/test_phase16_selection.py \
  tests/test_phase16_sharing.py \
  -q
```

## Layout

```text
my-RDagent-V3/
  pyproject.toml
  .importlinter
  skills/
    rd-agent/
    rd-propose/
    rd-code/
    rd-execute/
    rd-evaluate/
    rd-tool-catalog/
  v3/
    algorithms/
    contracts/
    entry/
    orchestration/
    ports/
    tools/
  tests/
```

## Continue This Session

If you are resuming from the current standalone planning session, start here:

- `.planning/STATE.md`
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-01-SUMMARY.md`
- `.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-02-SUMMARY.md`
