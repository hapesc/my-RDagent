---
name: "rd-code"
description: "Build-stage: advance branch from build toward verify in an existing standalone V3 run."
argument-hint: "--run <run_id> --branch <branch_id> | --continue"
allowed-tools:
  - Read
  - Bash
---

<codex_skill_adapter>
## Invocation
- Claude Code: `rd-code` skill
- Codex: `$rd-code`
- Treat text after skill mention as arguments.
## Tool mapping
- AskUserQuestion → request_user_input
</codex_skill_adapter>

<objective>
Complete, replay, or review the build stage for an existing V3 run and branch.
Hand off to rd-execute on success. Never starts the full loop — use rd-agent for that.

Maps to `rd_agent.entry.rd_code.rd_code`.
</objective>

<execution_context>
@skills/rd-code/workflows/continue.md
@skills/_shared/references/stage-contract.md
@skills/_shared/references/tool-execution-context.md
</execution_context>

<required_fields>
- run_id (string): the run identifier for the paused standalone V3 run
- branch_id (string): the branch that owns the current build step
- summary (string): the current-step summary to publish
- artifact_ids (list): the current-step artifact identifiers to publish or replay
</required_fields>

<process>
Execute the continue workflow from @skills/rd-code/workflows/continue.md end-to-end.
</process>

<outcome_guide>
- reused: published build evidence still valid → confirm and hand to rd-execute
- review: build needs manual review → surface reason, do NOT claim ready
- replay: build needs fresh publish → replay then hand to rd-execute
- completed: next skill is rd-execute
</outcome_guide>
