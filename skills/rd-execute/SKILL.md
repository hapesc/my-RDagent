---
name: "rd-execute"
description: "Verify-stage: complete or block verification before synthesize in an existing standalone V3 run."
argument-hint: "--run <run_id> --branch <branch_id> [--block <reasons>] | --continue"
allowed-tools:
  - Read
  - Bash
---

<codex_skill_adapter>
## Invocation
- Claude Code: `rd-execute` skill
- Codex: `$rd-execute`
- Treat text after skill mention as arguments.
## Tool mapping
- AskUserQuestion → request_user_input
</codex_skill_adapter>

<objective>
Complete, replay, review, or block the verify stage for an existing V3 run and
branch. Hand off to rd-evaluate on success, or publish blocking reasons.
Never starts the full loop — use rd-agent for that.

Maps to `v3.entry.rd_execute.rd_execute`.
</objective>

<execution_context>
@skills/rd-execute/workflows/continue.md
@skills/_shared/references/stage-contract.md
@skills/_shared/references/tool-execution-context.md
</execution_context>

<required_fields>
- run_id (string): the run identifier for the paused standalone V3 run
- branch_id (string): the branch that owns the current verify step
- summary (string): the current-step summary to publish
- artifact_ids (list): the current-step artifact identifiers to publish or replay
- blocking_reasons (list, optional): provide only when verification must stop as blocked
</required_fields>

## Tool execution context

- If this skill must drop to direct inspection or primitive tools, run `uv run rdagent-v3-tool ...` from the standalone V3 repo root or from the installed standalone V3 runtime bundle root that owns this skill.
- Do not run direct tools from the caller repo unless the caller repo is that standalone V3 runtime.
- Keep state inspection scoped to the current working repo's canonical V3 state or an explicitly provided state root.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` on the agent side when direct inspection of verification state or a concrete primitive is needed.
- Keep `rd-tool-catalog` as an agent-side escalation path rather than defaulting the operator into manual tool browsing.

<process>
Execute the continue workflow from @skills/rd-execute/workflows/continue.md end-to-end.
</process>

## Outcome guide

- `reused`: published verify evidence still valid → confirm and hand to rd-evaluate
- `review`: verify held for manual review → surface reason, do NOT claim ready
- `replay`: verify needs fresh publish → replay then hand to rd-evaluate
- `blocked`: publish explicit `blocking_reasons`, keep branch out of rd-evaluate handoff
- completed: the next high-level action is `rd-evaluate`
</outcome_guide>
