---
name: "rd-agent"
description: "Use for starting or continuing the standalone V3 loop when the caller wants the default high-level orchestration path across stages or branches."
---

# rd-agent

Primary orchestration skill for the standalone V3 surface.

Maps to `v3.entry.rd_agent.rd_agent`.

## Tool execution context

- When this skill downshifts to direct tools, run `uv run rdagent-v3-tool ...` from the standalone V3 repo root or from the installed standalone V3 runtime bundle root that owns this skill.
- Do not run direct tools from the caller repo unless the caller repo is that standalone V3 runtime.
- Inspect only the current working repo's canonical V3 state or an explicitly provided state root.
- If the current working repo has no canonical V3 state, do not search other repos or `HOME`; stay on the fresh-start path or ask only for the minimum start contract.

## Trigger requests

- "help me do this task"
- "what should I do next?"
- "start a V3 run"
- "continue the standalone loop"
- "run the full rd-agent flow"
- "use the default orchestration path"

## When to use

- Start from plain language first, then let `rd-agent` inspect persisted state and route to the right next high-level skill.
- Use this when a paused run may already exist and the agent should recommend the correct continuation path instead of silently opening a new run.
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

## Internal workflows

- Load `workflows/intent-routing.md` when processing plain-language intent or
  detecting paused-run continuation.
- Load `workflows/start-contract.md` when the operator needs the start payload,
  stop behavior, or example shape.

## References

- Load `references/failure-routing.md` when handling missing inputs, routing
  failures, or deciding between stage skills and rd-tool-catalog as an
  agent-side escalation path.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` only when the high-level `rd-agent` boundary is insufficient and the agent needs a concrete direct tool in the background.
- Route to `rd-tool-catalog` when the work is inspection-only or primitive-only and should not stay on the orchestration surface.
- After routing there, keep the direct-tool call in the same standalone V3 repo root or installed runtime bundle root rather than changing execution roots.
- Do not push the operator into manual tool selection for common start or continue flows; keep them on `rd-agent` unless a lower-level primitive is genuinely required.

## When not to use

- Do not use this when the caller already knows it only needs one stage entrypoint such as `rd-propose`, `rd-code`, `rd-execute`, or `rd-evaluate`.
- Do not use this when the task is only to inspect existing run, branch, stage, artifact, or memory state.
- Do not use this as a generic CLI catalog browser; use `rd-tool-catalog` for that.
- If blocked, route to: the corresponding stage skill (`rd-propose`, `rd-code`,
  `rd-execute`, `rd-evaluate`) or `rd-tool-catalog` for inspection-only tasks.
- If state absent, fresh-start only: do not search other repos or `HOME`; stay
  on the minimum start contract path.

## Output

- Start or continue the V3 orchestration flow through the canonical run and branch contracts.
- When routing plain-language intent, return the concise current-state, reason, next-action, and `recommended_next_skill` guidance before exposing lower-level detail.
- When the recommended path is blocked, include the repair action explicitly so the user sees the current executable step instead of a false-ready continuation claim.
- Use `detail_hint` when the route is healthy and the next move is already
  obvious.
- Use `next_step_detail` when the user is blocked or starting fresh and needs a
  one-line minimum command or skeleton.
- Prefer this skill before dropping to lower-level CLI primitives.

## Success contract

- Success means the skill either starts the run or advances the high-level loop with the canonical V3 run and branch contracts.
- If the task should not stay in `rd-agent`, the skill should explicitly route to a stage skill or to `rd-tool-catalog`.
