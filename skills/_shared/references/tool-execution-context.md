# Tool Execution Context

Shared rules for running direct CLI tools from any RD-Agent V3 skill.

## CLI invocation

- Run `uv run rdagent-tool ...` from the standalone V3 repo root or from the
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
uv run rdagent-tool list                # tool catalog
uv run rdagent-tool describe rd_run_get     # run-state tool schema
uv run rdagent-tool describe rd_branch_get  # branch-state tool schema
uv run rdagent-tool describe rd_stage_get   # stage-state tool schema
uv run rdagent-tool describe <tool>         # any tool details
```
