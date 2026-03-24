# Tool Execution Context

Shared rules for running direct CLI tools from any RD-Agent V3 skill.

## CLI invocation

- Run `uv run rdagent-v3-tool ...` from the standalone V3 repo root or from the
  installed standalone V3 runtime bundle root that owns this skill.
- Do not run direct tools from the caller repo unless the caller repo is that
  standalone V3 runtime.

## State scope

- Inspect only the current working repo's canonical V3 state or an explicitly
  provided state root.
- If the current working repo has no canonical V3 state, do not search other
  repos or `HOME`; stay on the fresh-start path or ask for the minimum start
  contract.

## Common inspection commands

```bash
uv run rdagent-v3-tool rd_run_get          # current run state
uv run rdagent-v3-tool rd_branch_get       # current branch state
uv run rdagent-v3-tool rd_stage_get        # current stage state
uv run rdagent-v3-tool list                # tool catalog
uv run rdagent-v3-tool describe <tool>     # tool details
```
