---
name: "rd-evaluate"
description: "Synthesize-stage: close iteration or continue back to framing in an existing standalone V3 run."
argument-hint: "--run <run_id> --branch <branch_id> --recommendation <continue|stop> | --continue"
allowed-tools:
  - Read
  - Bash
---

<codex_skill_adapter>
## Invocation
- Claude Code: `rd-evaluate` skill
- Codex: `$rd-evaluate`
- Treat text after skill mention as arguments.
## Tool mapping
- AskUserQuestion → request_user_input
</codex_skill_adapter>

<objective>
Complete or replay the synthesize stage for an existing V3 run and branch.
Return the branch decision as continue (back to rd-propose) or stop.
Never starts the full loop — use rd-agent for that.

Maps to `rd_agent.entry.rd_evaluate.rd_evaluate`.
</objective>

<execution_context>
@skills/rd-evaluate/workflows/continue.md
@skills/_shared/references/stage-contract.md
@skills/_shared/references/tool-execution-context.md
</execution_context>

<required_fields>
- run_id (string): the run identifier for the paused standalone V3 run
- branch_id (string): the branch that owns the current synthesize step
- summary (string): the current-step summary to publish
- artifact_ids (list): the current-step artifact identifiers to publish or replay
- recommendation (string): "continue" or "stop"
</required_fields>

<process>
Execute the continue workflow from @skills/rd-evaluate/workflows/continue.md end-to-end.
</process>

<outcome_guide>
- reused: published synthesize evidence still valid → honor existing recommendation
- review: synthesize needs manual review → surface reason, do NOT claim settled
- replay: synthesize needs fresh publish → replay then apply recommendation
- completed with continue: next skill is rd-propose (back to framing)
- completed with stop: loop ends, no next stage skill
</outcome_guide>
