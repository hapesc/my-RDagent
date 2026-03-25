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

Maps to `rd_agent.entry.rd_execute.rd_execute`.
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

<process>
Execute the continue workflow from @skills/rd-execute/workflows/continue.md end-to-end.
</process>

<outcome_guide>
- reused: published verify evidence still valid → confirm and hand to rd-evaluate
- review: verify held for manual review → surface reason, do NOT claim ready
- replay: verify needs fresh publish → replay then hand to rd-evaluate
- blocked: publish explicit blocking reasons, keep branch out of rd-evaluate handoff
- completed: next skill is rd-evaluate
</outcome_guide>
