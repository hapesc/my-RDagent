---
name: "rd-propose"
description: "Use for framing-stage work in an existing standalone V3 run when the caller already has branch context and wants to move from framing toward build."
---

# rd-propose

Framing-stage skill for the standalone V3 surface.

Maps to `v3.entry.rd_propose.rd_propose`.

## Trigger requests

- "complete the framing stage"
- "resume rd-propose"
- "advance this branch from framing to build"
- "replay the framing stage"

## When to use

- Complete or replay the framing stage for an existing run and branch.
- Use this when you already have `run_id`, `branch_id`, a framing summary, and framing artifact IDs.
- Use this when the task is specifically to move a branch from framing toward build.

## Continue contract

- Use this skill to continue a paused run inside one known step, not to restart the whole standalone flow.
- The operator-facing job is: continue the current framing step with the exact continuation identifiers and payload, then hand off the successful path to `rd-code`.
- Keep the interaction at the high-level skill layer unless the agent must inspect lower-level state to recover missing continuation details.

## Required fields

- `run_id`: the run identifier for the paused standalone V3 run.
- `branch_id`: the branch identifier that owns the current framing step.
- `summary`: the current-step summary to publish for this framing continuation.
- `artifact_ids`: the current-step artifact identifiers to publish or replay for this framing continuation.

## If information is missing

- First inspect current run or branch state instead of asking the operator to browse tools manually.
- Then surface the exact missing values, including which field names are still absent and which values the agent already derived from current state.
- Ask the operator only for values that cannot already be derived.
- If the agent still needs a direct inspection or recovery primitive, use `rd-tool-catalog` as an agent-side escalation path and return with the resolved continuation fields.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` on the agent side when you need direct inspection of run, branch, stage, artifact, or recovery state before or around framing.
- Route to `rd-tool-catalog` on the agent side when you need a specific CLI primitive instead of the stage entrypoint.
- Route to `rd-tool-catalog` when the high-level continuation boundary is insufficient, but keep the operator on the `rd-propose` path rather than telling them to browse tools first.

## When not to use

- Do not use this to start a new end-to-end workflow; use `rd-agent` for the default orchestration path.
- Do not use this when the branch is already in build, verify, or synthesize and the task belongs to a later stage.
- Do not use this as a general tool discovery surface.

## Failure handling

- If `run_id`, `branch_id`, `summary`, or `artifact_ids` are missing, inspect current run or branch state, surface the exact missing values, and ask only for the unresolved prerequisites rather than guessing them.
- If the caller only needs inspection or one direct primitive after that check, use `rd-tool-catalog` as the agent-side escalation path.
- If the branch is not actually in the framing stage, route to the correct stage skill or back to `rd-agent`.

## Output

- Applies the framing-stage transition rules and prepares the branch for `rd-code` when appropriate.

## Outcome guide

- `reused`: published framing evidence is still valid; confirm the reuse result and move to `rd-code`.
- `review`: framing cannot safely continue yet; surface the review reason, identify the missing or blocked state, and do not claim the branch is ready for `rd-code`.
- `replay`: framing needs a fresh publish; replay the framing step with the recovered continuation payload, then hand the normal path to `rd-code`.
- completed: the next high-level action is `rd-code`.

## Success contract

- Success means the framing-stage transition is applied, replayed, reused, or reviewed against the canonical V3 state.
- The skill should leave the branch ready for `rd-code` when the framing stage completes normally.
