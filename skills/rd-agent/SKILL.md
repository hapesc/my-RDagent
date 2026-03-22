---
name: "rd-agent"
description: "Use for starting or continuing the standalone V3 loop when the caller wants the default high-level orchestration path across stages or branches."
---

# rd-agent

Primary orchestration skill for the standalone V3 surface.

Maps to `v3.entry.rd_agent.rd_agent`.

## Trigger requests

- "start a V3 run"
- "continue the standalone loop"
- "run the full rd-agent flow"
- "use the default orchestration path"

## When to use

- Start a new V3 run from a task summary and scenario label.
- Run the full high-level loop instead of calling stage skills one by one.
- Use this when you want the default orchestration path across single-branch and multi-branch execution.

## Required fields

- `title`
- `task_summary`
- `scenario_label`
- `stage_inputs.framing.summary`
- `stage_inputs.framing.artifact_ids`

## Optional fields

- `initial_branch_label`
- `execution_mode`
- `max_stage_iterations`
- `branch_hypotheses`

## Minimum start contract

The strict minimum to start `rd-agent` is a run title, a task summary, a scenario label, and the first-step payload. In public field terms, that means `title`, `task_summary`, `scenario_label`, `stage_inputs.framing.summary`, and `stage_inputs.framing.artifact_ids`.

Use this minimum contract when you only need one concrete starting path and do not need the richer multi-branch setup yet. The first-step payload is the current-step summary plus the artifact ids that support it; the first internal step is `framing`, but the operator-facing truth is still the literal field names above.

## Recommended multi-branch contract

The recommended path is still skill-first: start with the minimum contract, then add optional control fields when the task benefits from multiple candidate approaches. In practice that usually means keeping the required fields above, setting any explicit execution controls you need, and adding `branch_hypotheses` so `rd-agent` can open a richer multi-branch path instead of a single branch only.

Example recommended payload shape:

```text
title="Skill contract hardening"
task_summary="Drive the standalone loop for the operator-guidance phase."
scenario_label="research"
stage_inputs.framing.summary="Framing is complete with a concrete execution plan."
stage_inputs.framing.artifact_ids=["artifact-plan-001"]
initial_branch_label="primary"
execution_mode="gated"
max_stage_iterations=1
branch_hypotheses=["primary", "lighter-doc-pass", "regression-first"]
```

Keep the two layers distinct: `branch_hypotheses` is recommended for the richer path, but it is not part of the strict minimum start contract.

## Default stop behavior

The default operator path is `gated + max_stage_iterations=1`. In plain language, `rd-agent` will complete the current step, then pause for human review before continuing. The next step is created and ready, but the next step is prepared but is not continued automatically.

If you stay on the default path, the public stop reason is `awaiting_operator`. Internally the first step maps to `framing`, but the main operating rule is simpler: one step finishes, the following step is queued up, and the run stops so a human can review before more work happens.

If you switch to a more continuous unattended path, `rd-agent` can advance further before stopping. Use that only when you want fewer review pauses and you are intentionally changing the default safety boundary.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` only when the high-level `rd-agent` boundary is insufficient and the agent needs a concrete direct tool in the background.
- Route to `rd-tool-catalog` when the work is inspection-only or primitive-only and should not stay on the orchestration surface.
- Do not push the operator into manual tool selection for common start or continue flows; keep them on `rd-agent` unless a lower-level primitive is genuinely required.

## When not to use

- Do not use this when the caller already knows it only needs one stage entrypoint such as `rd-propose`, `rd-code`, `rd-execute`, or `rd-evaluate`.
- Do not use this when the task is only to inspect existing run, branch, stage, artifact, or memory state.
- Do not use this as a generic CLI catalog browser; use `rd-tool-catalog` for that.

## Failure handling

- If the caller is missing inputs, inspect current run or branch state first, surface the exact missing values you can already derive, and ask the operator only for the values that still cannot be derived.
- If the caller is missing the inputs needed to start or continue the orchestration flow, do not invent them and do not send the operator to browse tools manually.
- If the task turns out to be stage-specific rather than full-loop orchestration, route to the corresponding stage skill.
- If the task is inspection- or primitive-only, use `rd-tool-catalog` as an agent-side escalation path instead of forcing the orchestration wrapper.

## If information is missing

- Inspect current run or branch state before asking for more input.
- Surface the exact missing values, not a vague request for "more context."
- Only ask the operator for values that cannot already be derived from the existing run, branch, or artifact state.
- If the missing information proves the task is really stage-specific, route to the corresponding stage skill instead of stretching `rd-agent` past its boundary.

## Output

- Start or continue the V3 orchestration flow through the canonical run and branch contracts.
- Prefer this skill before dropping to lower-level CLI primitives.

## Success contract

- Success means the skill either starts the run or advances the high-level loop with the canonical V3 run and branch contracts.
- If the task should not stay in `rd-agent`, the skill should explicitly route to a stage skill or to `rd-tool-catalog`.
