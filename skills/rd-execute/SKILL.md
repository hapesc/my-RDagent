---
name: "rd-execute"
description: "Use for verify-stage work in an existing standalone V3 run when the caller already has branch context and wants to complete or block verification before synthesize."
---

# rd-execute

Verify-stage skill for the standalone V3 surface.

Maps to `v3.entry.rd_execute.rd_execute`.

## Tool execution context

- If this skill must drop to direct inspection or primitive tools, run `uv run rdagent-v3-tool ...` from the standalone V3 repo root or from the installed standalone V3 runtime bundle root that owns this skill.
- Do not run direct tools from the caller repo unless the caller repo is that standalone V3 runtime.
- Keep state inspection scoped to the current working repo's canonical V3 state or an explicitly provided state root.

## Trigger requests

- "complete the verify stage"
- "resume rd-execute"
- "block this branch with verification reasons"
- "advance this branch from verify to synthesize"

## When to use

- Complete, replay, or block the verify stage for an existing run and branch.
- Use this when you already have `run_id`, `branch_id`, a verify summary, and verify artifact IDs.
- Use this when the task is specifically to move a branch from verify toward synthesize or to record blocking reasons.

## Internal workflows

- Load `workflows/continue.md` when continuing a paused verify step with known
  `run_id` and `branch_id`.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` on the agent side when you need direct inspection of stage state, recovery state, or a verification-related primitive.
- Route to `rd-tool-catalog` on the agent side when you need to select a specific `inspection` or `primitives` tool instead of using the verify-stage wrapper.
- Keep those direct-tool calls in the same standalone V3 repo root or installed runtime bundle root after routing.
- Route to `rd-tool-catalog` when the high-level verification boundary is insufficient, but do not make manual tool browsing the default continuation path for the operator.

## When not to use

- Do not use this to start the overall workflow; use `rd-agent` first for the default orchestration path.
- Do not use this for framing, build, or synthesize ownership when the branch is in another stage.
- Do not use this as a general-purpose catalog interface.
- If blocked, route to: `rd-agent` for full-loop restart, or the correct stage
  skill if the branch is in another stage.
- If state absent, fresh-start only: do not fabricate continuation context;
  route to `rd-agent` for the minimum start contract.

## Failure handling

- If `run_id`, `branch_id`, `summary`, or `artifact_ids` are missing, inspect current run or branch state, surface the exact missing values, and ask only for the unresolved continuation inputs instead of guessing them.
- If the blocked path is required but `blocking_reasons` is still unresolved after inspection, ask only for the blocking reasons that cannot be derived from current verification state.
- If the task is only to inspect state or choose a direct primitive after that recovery step, use `rd-tool-catalog` as the agent-side escalation path.
- If the branch belongs to another stage, route to the correct stage skill or back to `rd-agent`.

## Output

- Applies verify-stage transitions and records either completion or blocking reasons before the synthesize stage.

## Outcome guide

- `reused`: published verify evidence is still valid; confirm the reuse result and move to `rd-evaluate`.
- `review`: verify is held for manual review; surface the review reason and do not claim the branch is ready for `rd-evaluate`.
- `replay`: verify needs a fresh publish; replay the step with the recovered continuation payload, then continue with `rd-evaluate` when the normal path is restored.
- `blocked`: publish explicit blocking reasons, keep the branch out of the normal `rd-evaluate` handoff, and tell the operator what must be resolved before verification can continue.
- completed: the next high-level action is `rd-evaluate`.

## Success contract

- Success means the verify-stage transition is applied, replayed, reused, reviewed, or blocked against canonical V3 state.
- The skill should either leave the branch ready for `rd-evaluate` or return explicit blocking reasons.
