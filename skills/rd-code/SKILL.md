---
name: "rd-code"
description: "Use for build-stage work in an existing standalone V3 run when the caller already has branch context and wants to move from build toward verify."
---

# rd-code

Build-stage skill for the standalone V3 surface.

Maps to `v3.entry.rd_code.rd_code`.

## Tool execution context

- If this skill must drop to direct inspection or primitive tools, run `uv run rdagent-v3-tool ...` from the standalone V3 repo root or from the installed standalone V3 runtime bundle root that owns this skill.
- Do not run direct tools from the caller repo unless the caller repo is that standalone V3 runtime.
- Keep state inspection scoped to the current working repo's canonical V3 state or an explicitly provided state root.

## Trigger requests

- "complete the build stage"
- "resume rd-code"
- "advance this branch from build to verify"
- "replay the build stage"

## When to use

- Complete or replay the build stage for an existing run and branch.
- Use this when you already have `run_id`, `branch_id`, a build summary, and build artifact IDs.
- Use this when the task is specifically to advance a branch from build toward verify.

## Internal workflows

- Load `workflows/continue.md` when continuing a paused build step with known
  `run_id` and `branch_id`.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` on the agent side when you need direct inspection of build-stage state, artifacts, or recovery decisions.
- Route to `rd-tool-catalog` on the agent side when you need one concrete primitive tool instead of the build-stage wrapper.
- Keep those direct-tool calls in the same standalone V3 repo root or installed runtime bundle root after routing.
- Route to `rd-tool-catalog` when the task is better served by category-guided CLI tool selection, but keep the operator on the `rd-code` continuation path rather than defaulting to manual tool browsing.

## When not to use

- Do not use this to orchestrate the full V3 loop; use `rd-agent` for that.
- Do not use this when the work belongs to framing, verify, or synthesize rather than build.
- Do not use this as a passive catalog or documentation surface.
- If blocked, route to: `rd-agent` for full-loop restart, or the correct stage
  skill if the branch is in another stage.
- If state absent, fresh-start only: do not fabricate continuation context;
  route to `rd-agent` for the minimum start contract.

## Failure handling

- If `run_id`, `branch_id`, `summary`, or `artifact_ids` are missing, inspect current run or branch state, surface the exact missing values, and ask only for the unresolved continuation inputs instead of fabricating stage context.
- If the task is inspection- or primitive-oriented after that recovery step, use `rd-tool-catalog` as the agent-side escalation path.
- If the branch belongs to another stage, route to the correct stage skill or back to `rd-agent`.

## Output

- Applies the build-stage transition rules and prepares the branch for `rd-execute` when appropriate.

## Outcome guide

- `reused`: published build evidence is still valid; confirm the reuse result and move to `rd-execute`.
- `review`: build needs manual review or clearer state before it can continue; surface that reason and do not claim the branch is ready for `rd-execute`.
- `replay`: build must publish fresh evidence; replay the build step with the recovered continuation payload, then continue with `rd-execute`.
- completed: the next high-level action is `rd-execute`.

## Success contract

- Success means the build-stage transition is applied, replayed, reused, or reviewed against the canonical V3 state.
- The skill should leave the branch ready for `rd-execute` when the build stage completes normally.
