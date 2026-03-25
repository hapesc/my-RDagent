---
name: "rd-agent"
description: "Start or continue the V3 orchestration loop — intent routing, paused-run detection, stage dispatch."
argument-hint: "<task description> | --continue | --status"
allowed-tools:
  - Read
  - Bash
  - Glob
---

<codex_skill_adapter>
## Invocation
- Claude Code: `rd-agent` skill
- Codex: `$rd-agent`
- Treat text after skill mention as arguments.
## Tool mapping
- AskUserQuestion → request_user_input
</codex_skill_adapter>

<objective>
Primary orchestration entry for standalone V3. Routes plain-language intent to
the correct stage skill (rd-propose, rd-code, rd-execute, rd-evaluate) or
detects and continues paused runs. Never executes stage logic directly.

Maps to `rd_agent.entry.rd_agent.rd_agent`.
</objective>

## Required fields

Start path:
- `title`
- `task_summary`
- `scenario_label`
- `stage_inputs.framing.summary`
- `stage_inputs.framing.artifact_ids`

Continue path:
- none; the paused-run path is derived from persisted state

## Optional fields

- `initial_branch_label`
- `execution_mode`
- `max_stage_iterations`
- `branch_hypotheses`
- `hypothesis_specs`
- `holdout_evaluation_port`
- `holdout_split_port`

## Tool execution context

Use `uv run rdagent-tool ...` only from the installed standalone V3 runtime bundle root or a checked-out standalone V3 repo root; do not search other repos or `HOME` for a plausible state directory.

## When to route to rd-tool-catalog

Use `rd-tool-catalog` only as an agent-side escalation path when the agent needs a concrete direct tool in the background. Do not push the operator into manual tool selection for common start or continue flows.

## Success contract

`rd-agent` starts the run or advances the high-level loop, then either keeps ownership on the orchestration surface or tells the operator to route to a stage skill or to `rd-tool-catalog`.

<execution_context>
@skills/rd-agent/workflows/intent-routing.md
@skills/rd-agent/workflows/start-contract.md
@skills/_shared/references/failure-routing.md
@skills/_shared/references/tool-execution-context.md
@skills/_shared/references/output-conventions.md
</execution_context>

<required_fields>
Start path:
  - title (string)
  - task_summary (string)
  - scenario_label (string)
  - stage_inputs.framing.summary (string)
  - stage_inputs.framing.artifact_ids (list)

Continue path:
  - (none — detected from persisted state)

Optional:
  - initial_branch_label
  - execution_mode
  - max_stage_iterations
  - branch_hypotheses
  - hypothesis_specs (advanced structured multi-branch path)
  - holdout_evaluation_port (required when hypothesis_specs is provided)
  - holdout_split_port (optional override for structured holdout splitting)
</required_fields>

<process>
Execute intent-routing workflow from @skills/rd-agent/workflows/intent-routing.md.
If start contract needed, also load @skills/rd-agent/workflows/start-contract.md.
</process>

<routing_boundary>
- Route to rd-tool-catalog only when the high-level rd-agent boundary is
  insufficient and the agent needs a concrete direct tool.
- Route to rd-tool-catalog for inspection-only or primitive-only work that
  should not stay on the orchestration surface.
- Do not push the operator into manual tool selection for common start or
  continue flows.
</routing_boundary>
