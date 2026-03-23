---
name: "rd-propose"
description: "Use for framing-stage work in an existing standalone V3 run when the caller already has branch context and wants to move from framing toward build."
---

# rd-propose

Framing-stage skill for the standalone V3 surface.

Maps to `v3.entry.rd_propose.rd_propose`.

## Tool execution context

- If this skill must drop to direct inspection or primitive tools, run `uv run rdagent-v3-tool ...` from the standalone V3 repo root or from the installed standalone V3 runtime bundle root that owns this skill.
- Do not run direct tools from the caller repo unless the caller repo is that standalone V3 runtime.
- Keep state inspection scoped to the current working repo's canonical V3 state or an explicitly provided state root.

## Trigger requests

- "complete the framing stage"
- "resume rd-propose"
- "advance this branch from framing to build"
- "replay the framing stage"

## When to use

- Complete or replay the framing stage for an existing run and branch.
- Use this when you already have `run_id`, `branch_id`, a framing summary, and framing artifact IDs.
- Use this when the task is specifically to move a branch from framing toward build.

## Internal workflows

- Load `workflows/continue.md` when continuing a paused framing step with known
  `run_id` and `branch_id`.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` on the agent side when you need direct inspection of run, branch, stage, artifact, or recovery state before or around framing.
- Route to `rd-tool-catalog` on the agent side when you need a specific CLI primitive instead of the stage entrypoint.
- Keep those direct-tool calls in the same standalone V3 repo root or installed runtime bundle root after routing.
- Route to `rd-tool-catalog` when the high-level continuation boundary is insufficient, but keep the operator on the `rd-propose` path rather than defaulting to manual tool browsing.

## When not to use

- Do not use this to start a new end-to-end workflow; use `rd-agent` for the default orchestration path.
- Do not use this when the branch is already in build, verify, or synthesize and the task belongs to a later stage.
- Do not use this as a general tool discovery surface.
- If blocked, route to: `rd-agent` for full-loop restart, or the correct stage
  skill if the branch is in another stage.
- If state absent, fresh-start only: do not fabricate continuation context;
  route to `rd-agent` for the minimum start contract.

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
