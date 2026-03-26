# my-RDagent

Agent-first research and development loop: propose, code, execute, evaluate, repeat.

## What This Repo Ships

- **Skills** under `skills/` — high-level orchestration (`rd-agent`) and
  stage-specific skills (`rd-propose`, `rd-code`, `rd-execute`, `rd-evaluate`)
- **CLI tool catalog** via `rdagent-tool` — direct inspection and primitive
  operations for when a skill boundary is insufficient
- **Python package** `rd_agent` — contracts, orchestration services, ports, and
  algorithms backing the skill and CLI surfaces
- **Tests** — regression suites that lock the public surface and contracts

The public surface is transport-free: skills first, CLI tools second, no
server abstraction.

## Repository Setup

```bash
uv sync --extra test
```

One-command setup with skill installation and verification:

```bash
bash scripts/setup_env.sh                           # Claude, local, quick
bash scripts/setup_env.sh --all --scope-all --full-verify  # everything
```

## Agent Skill Setup

The installer copies canonical `skills/` packages into Claude/Codex runtime
roots and creates a managed runtime bundle for CLI tool execution.

```bash
# Local install (repo-scoped)
uv run python scripts/install_agent_skills.py --runtime claude --scope local
uv run python scripts/install_agent_skills.py --runtime codex --scope local

# Global install (home-scoped)
uv run python scripts/install_agent_skills.py --runtime claude --scope global
uv run python scripts/install_agent_skills.py --runtime codex --scope global
```

Files are copied — the install is self-contained and independent of the source repo.

The installer writes:

- Skills into `.codex/skills/` or `.claude/skills/` (local) or `~/.codex/skills/` / `~/.claude/skills/` (global)
- A managed standalone runtime bundle at `.codex/rd-agent/`, `.claude/rd-agent/`, `~/.codex/rd-agent/`, or `~/.claude/rd-agent/`

Direct CLI catalog commands should be called from that installed runtime bundle
root, not from an unrelated caller repo.

## Start -> Inspect -> Continue

The operator playbook for using the pipeline.

### Start

Use `rd-agent` first. It routes plain-language intent through persisted state:

- If a paused run exists, it recommends the matching continuation skill
- If preflight blockers exist, it surfaces the blocker and a repair action
- If starting fresh, it recommends multi-branch exploration by default

For the public start contract, see `skills/rd-agent/SKILL.md`.

### Inspect

Inspect current state before continuing. Use the skill contract first; drop to
`rd-tool-catalog` only when you need a specific CLI tool:

```bash
cd ~/.codex/rd-agent
uv run rdagent-tool list
uv run rdagent-tool describe rd_run_start
```

### Continue

Route to the stage skill matching the paused run:

| Stage | Skill | Entrypoint |
|-------|-------|------------|
| Framing | `rd-propose` | `rd_agent.entry.rd_propose.rd_propose` |
| Build | `rd-code` | `rd_agent.entry.rd_code.rd_code` |
| Verify | `rd-execute` | `rd_agent.entry.rd_execute.rd_execute` |
| Synthesize | `rd-evaluate` | `rd_agent.entry.rd_evaluate.rd_evaluate` |

Each skill package at `skills/<name>/SKILL.md` has the exact continuation
contract and field-level details.

## Default Orchestration

- Skill: `skills/rd-agent/SKILL.md`
- Entrypoint: `rd_agent.entry.rd_agent.rd_agent`
- Purpose: start or continue the loop across single-branch and multi-branch
  execution

Two multi-branch contracts:

- `branch_hypotheses` — label-only multi-branch exploration (legacy)
- `hypothesis_specs` — structured exploration with DAG topology, parent
  selection, dynamic pruning, cross-branch sharing, holdout finalization, and
  standardized ranking. Requires `holdout_evaluation_port`; defaults are
  available via `rd_agent.ports.defaults`

When finalization completes, the response is finalization-first: the holdout
winner is the selected branch.

## CLI Tool Catalog

- Skill: `skills/rd-tool-catalog/SKILL.md`
- Module: `rd_agent.entry.tool_catalog`
- CLI: `rdagent-tool`

```bash
uv run rdagent-tool list                       # list all tools
uv run rdagent-tool describe rd_run_start      # inspect one tool
uv run rdagent-tool describe rd_explore_round
```

Tool categories: `orchestration`, `inspection`, `primitives`.
Primitive subcategories: `branch_lifecycle`, `branch_knowledge`,
`branch_selection`, `memory`.

## Routing Model

1. **`rd-agent`** — default entry unless already inside a known stage
2. **Stage skills** — `rd-propose` / `rd-code` / `rd-execute` / `rd-evaluate`
   when working inside one owned stage
3. **`rd-tool-catalog`** — selective downshift when a skill boundary is
   insufficient
4. **Narrow by category** → primitive `subcategory` → specific tool

## Verification

Quick gate:

```bash
make test-quick
```

Full gate:

```bash
make test
make lint
uv run lint-imports
```

## Layout

```text
my-RDagent/
  pyproject.toml
  .importlinter
  Makefile
  scripts/
    setup_env.sh
    install_agent_skills.py
    bump_version.py
  skills/
    _shared/references/         # cross-skill shared context
    rd-agent/                   # orchestration skill
      SKILL.md
      workflows/
      references/
    rd-propose/                 # framing stage
    rd-code/                    # build stage
    rd-execute/                 # verify stage
    rd-evaluate/                # synthesize stage
    rd-tool-catalog/            # CLI tool inspection
  rd_agent/
    algorithms/                 # pure math: decay, PUCT, pruning, holdout, merge
    compat/legacy/              # legacy translation seam (isolated)
    contracts/                  # pydantic data contracts
    devtools/                   # skill installer
    entry/                      # public entrypoints and CLI
    orchestration/              # service layer
    ports/                      # abstract ports + defaults
    tools/                      # CLI tool implementations
  tests/
```
