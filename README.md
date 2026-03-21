# my-RDagent-V3

Standalone V3 extraction from `my-RDagent`, focused on the clean-split
agent-facing architecture rather than the legacy V1/V2 runtime shell.

## Scope

This repository contains the minimum self-contained V3 surface:

- `v3/contracts`
  - public run, branch, stage, recovery, memory, isolation, and exploration contracts
- `v3/orchestration`
  - single-branch and multi-branch coordination, recovery, stage transitions, memory, selection, pruning, sharing, convergence
- `v3/tools`
  - in-process tool handlers over V3-owned contracts and orchestration
- `v3/entry`
  - skill entrypoints such as `rd_agent`, `rd_propose`, `rd_code`, `rd_execute`, `rd_evaluate`
  - CLI-oriented tool catalog via `rdagent-v3-tool`
- `tests`
  - focused coverage for the extracted V3 surface

Deliberately excluded:

- legacy `app/`, `core/`, control-plane, FastAPI UI/server layers
- MCP transport/server wiring
- historical `exploration_manager` algorithm package

## Install

```bash
uv venv
uv sync --extra test
```

## CLI Tool Surface

List the available V3 CLI tools:

```bash
rdagent-v3-tool list
```

Describe one tool and inspect its schemas:

```bash
rdagent-v3-tool describe rd_run_start
rdagent-v3-tool describe rd_explore_round
```

The tool catalog is schema-described and transport-free. It is meant to back
skill and CLI workflows directly, not an MCP server.

## Skill Entrypoints

Primary skill entrypoints live under `v3.entry`:

- `rd_agent`
- `rd_propose`
- `rd_code`
- `rd_execute`
- `rd_evaluate`

`rd_agent` keeps the Phase 14 single-branch path and the Phase 16 multi-branch
path in the same V3-owned entry layer.

## Verification

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
  v3/
    algorithms/
    contracts/
    entry/
    orchestration/
    ports/
    tools/
  tests/
```

## Current Position

This extraction is meant to be a clean starting point for:

- evolving the V3 product surface independently
- building skill-first and CLI-first workflows
- adding a new external API or transport later, on top of the V3-owned core

## Continue This Session

If you are resuming from the extraction session, start here:

- `.planning/STATE.md`
- `.planning/V3-EXTRACTION-HANDOFF.md`
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/v1.0-v1.0-MILESTONE-AUDIT.md`
- `.planning/phases/16-multi-branch-orchestration-and-tool-surface-completion/16-VERIFICATION.md`
