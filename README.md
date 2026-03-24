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

## Repository Setup

```bash
uv sync --extra test
```

If you want a single command that sets up the repo environment, installs skills,
and runs verification, use:

```bash
bash scripts/setup_env.sh
```

The default path is `--claude --local --link --quick-verify`. For a
non-interactive all-runtime install similar to GSD, use:

```bash
bash scripts/setup_env.sh --all --scope-all --full-verify
```

Run all CLI commands from this repo environment. The standalone contract is:

- skill discovery comes from linking `skills/` into Claude/Codex skill roots
- CLI execution stays repo-local through `uv run ...`
- validation also runs from the cloned repo environment

## Agent Skill Setup

Use the repo-local installer to expose the canonical `skills/` packages to
Codex or Claude Code while also installing a managed standalone V3 runtime bundle
into the target runtime root.

Install into repo-local Codex and Claude roots:

```bash
uv run python scripts/install_agent_skills.py --runtime codex --scope local --mode link
uv run python scripts/install_agent_skills.py --runtime claude --scope local --mode link
```

Install into global Codex and Claude roots:

```bash
uv run python scripts/install_agent_skills.py --runtime codex --scope global --mode link
uv run python scripts/install_agent_skills.py --runtime claude --scope global --mode link
```

`link` is the default and preferred mode because it keeps the repo-local
runtime and skill assets as the single source of truth while still generating a
managed runtime bundle plus installed skills under the target runtime root.

The installer writes:

- installed skills under `./.codex/skills` or `./.claude/skills` for local installs, and under `~/.codex/skills` or `~/.claude/skills` for global installs
- a managed standalone runtime bundle under `./.codex/rdagent-v3`, `./.claude/rdagent-v3`, `~/.codex/rdagent-v3`, or `~/.claude/rdagent-v3`

Direct V3 CLI tools should be called from that installed runtime bundle root,
not from an unrelated caller repo.

## Start -> Inspect -> Continue

Use this as the public operator playbook for the standalone V3 surface.
Start from the high-level orchestration skill, inspect when the next surface
needs to be confirmed, then continue through the stage skill that matches the
paused run.

The routing default is intent-first: a user can describe work in plain
language, the surface inspects persisted state, and the reply compresses to
current state, why that route was chosen, the exact next action, the
`recommended_next_skill`, and when needed one blocker plus one repair action.
The default answer stays at current state, reason, and exact next action. It
only expands into a one-line minimum command or skeleton when the user is
blocked or starting fresh.

### Start

Use `rd-agent` first for the default standalone orchestration path.
Start with the recommended multi-branch path when the task benefits from multiple candidate approaches.
For simpler tasks, the strict minimum single-branch start contract from `skills/rd-agent/SKILL.md` is enough.
If a paused run already exists, `rd-agent` should say so first and recommend
the matching continuation skill instead of silently opening a new run. That
recommendation can still be blocked by canonical preflight truth; when that
happens the reply should keep the same `recommended_next_skill` and add the
current blocker plus a repair action.
Healthy paused runs should stay terse by default. Fresh-start replies and
blocked replies may add a one-line minimum command or skeleton so the user can
act immediately without spelunking for field contracts.

Keep the README at the decision level: start from `skills/rd-agent/SKILL.md`
for the public start contract, then use the exact field-level contract in that
skill package when you need the concrete payload shape.

### Inspect

Inspect before continuing when the agent needs to confirm the current state, the correct next surface, or the exact continuation contract.
The agent should inspect current state, identify the next valid step, and present it to the user.
Use `skills/rd-tool-catalog/SKILL.md` and `uv run rdagent-v3-tool describe rd_run_start` only as the selective downshift path when the high-level skill boundary is insufficient.

Inspect the relevant skill contract first when the next move is still
high-level. Downshift to `rd-tool-catalog` only when the agent needs one
concrete CLI tool or lower-level inspection detail in the background.
When that downshift happens, call direct tools from the installed standalone
runtime bundle root or from a checked-out standalone V3 repo root:

```bash
cd ~/.codex/rdagent-v3
uv run rdagent-v3-tool list
uv run rdagent-v3-tool describe rd_run_start
```

### Continue

If a paused run is still in framing, continue from
`skills/rd-propose/SKILL.md` rather than restarting the whole loop. Later
paused stages should route to `skills/rd-code/SKILL.md`,
`skills/rd-execute/SKILL.md`, and `skills/rd-evaluate/SKILL.md` for the exact
continue contract and field-level details.

One representative pattern is: start with `rd-agent`, inspect the current
state before handing off, then continue the paused run with the stage skill
that matches the current step instead of making the user browse direct tools
manually.

In default operator wording, that reply should read like:

- Current state: paused run X on branch Y is at build.
- Reason: paused run continuation is a stronger routing anchor than starting fresh.
- Next action: run the repair action first, then continue with `rd-code`.
- `recommended_next_skill`: `rd-code`
- repair action: `uv sync --extra test`

When the route is healthy but obvious, the reply may stop there and offer a
detail hint instead of dumping every continuation field. When the route is
blocked or starting fresh, the reply may append a one-line minimum command or
skeleton.

## Default Orchestration

This section is the supporting reference behind the `Start` step above. Use
`rd-agent` as the default orchestration entrypoint when you want the main
standalone flow instead of a narrower stage or tool surface.

- Skill package: `skills/rd-agent/SKILL.md`
- Python entrypoint: `v3.entry.rd_agent.rd_agent`
- Purpose: start or continue the standalone V3 loop across single-branch and
  multi-branch execution

`rd-agent` is the default orchestration path because it keeps the high-level
run, branch, and stage flow inside V3-owned orchestration instead of forcing
the caller to choose direct primitives up front. It is also the correct public
entry when the caller only says "help me do this task" or "what should I do
next?" and needs state-aware routing.

For advanced Python-entrypoint callers, the multi-branch surface now has two
distinct contracts:

- `branch_hypotheses`: legacy label-only multi-branch exploration
- `hypothesis_specs`: structured multi-branch exploration with DAG + holdout
  finalization; this path requires `holdout_evaluation_port` and may optionally
  override `holdout_split_port` (default: `StratifiedKFoldSplitter()`)

When structured multi-branch exploration reaches finalization, the public
response should be treated as finalization-first: the selected branch is the
holdout winner and the next action is to review the final submission rather
than continue convergence/fallback routing.

## Stage Skills

This section supports the `Continue` step above. When the caller already knows
it is working inside one owned paused stage, use the stage-specific skills in
this order:

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
end-to-end orchestration path, then follow the linked `SKILL.md` file for the
exact continuation fields.

## CLI Tool Catalog

This section is the supporting reference behind the `Inspect` downshift rule.
Use `rd-tool-catalog` as the selective downshift layer when a high-level skill
boundary is insufficient and you need one direct CLI tool.

- Skill package: `skills/rd-tool-catalog/SKILL.md`
- Catalog module: `v3.entry.tool_catalog`
- CLI entrypoint: `rdagent-v3-tool`

List the available V3 CLI tools:

```bash
uv run rdagent-v3-tool list
```

Describe one tool and inspect its schemas:

```bash
uv run rdagent-v3-tool describe rd_run_start
uv run rdagent-v3-tool describe rd_explore_round
```

Run those commands from the installed standalone runtime bundle root or from a
checked-out standalone V3 repo root. Do not run them from an unrelated caller repo
and do not search `HOME` for a plausible state directory.

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

Use this as the compact routing summary behind the `Start -> Inspect ->
Continue` mainline:

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

## Quick verification

Use the quick gate after cloning the repo or updating doc/setup surfaces:

```bash
uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q
```

## Full verification

Run the full standalone gate before calling packaging and planning continuity
hardened:

```bash
uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q
uv run lint-imports
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
