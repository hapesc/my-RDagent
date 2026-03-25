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

<process>
Execute the continue workflow from @skills/rd-propose/workflows/continue.md end-to-end.
</process>

<outcome_guide>
- reused: published framing evidence still valid → confirm and hand to rd-code
- review: framing cannot safely continue → surface reason, do NOT claim ready
- replay: framing needs fresh publish → replay then hand to rd-code
- completed: next skill is rd-code
</outcome_guide>
