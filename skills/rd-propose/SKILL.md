---
name: "rd-propose"
description: "Framing-stage: advance branch from framing toward build in an existing standalone V3 run."
argument-hint: "--run <run_id> --branch <branch_id> | --continue"
allowed-tools:
  - Read
  - Bash
---

<codex_skill_adapter>
## Invocation
- Claude Code: `rd-propose` skill
- Codex: `$rd-propose`
- Treat text after skill mention as arguments.
## Tool mapping
- AskUserQuestion → request_user_input
</codex_skill_adapter>

<objective>
Complete, replay, or review the framing stage for an existing V3 run and branch.
Hand off to rd-code on success. Never starts the full loop — use rd-agent for that.

Maps to `v3.entry.rd_propose.rd_propose`.
</objective>

<execution_context>
@skills/rd-propose/workflows/continue.md
@skills/_shared/references/stage-contract.md
@skills/_shared/references/tool-execution-context.md
</execution_context>

<required_fields>
- run_id (string): the run identifier for the paused standalone V3 run
- branch_id (string): the branch that owns the current framing step
- summary (string): the current-step summary to publish
- artifact_ids (list): the current-step artifact identifiers to publish or replay
</required_fields>

## Tool execution context

- If this skill must drop to direct inspection or primitive tools, run `uv run rdagent-v3-tool ...` from the standalone V3 repo root or from the installed standalone V3 runtime bundle root that owns this skill.
- Do not run direct tools from the caller repo unless the caller repo is that standalone V3 runtime.
- Keep state inspection scoped to the current working repo's canonical V3 state or an explicitly provided state root.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` on the agent side when direct inspection or one concrete primitive is needed around framing.
- Keep `rd-tool-catalog` as an agent-side escalation path rather than defaulting the operator into manual tool browsing.

<process>
Execute the continue workflow from @skills/rd-propose/workflows/continue.md end-to-end.
</process>

## Outcome guide

- `reused`: published framing evidence still valid → confirm and hand to rd-code
- `review`: framing cannot safely continue → surface reason, do NOT claim ready
- `replay`: framing needs fresh publish → replay then hand to rd-code
- completed: the next high-level action is `rd-code`
</outcome_guide>
