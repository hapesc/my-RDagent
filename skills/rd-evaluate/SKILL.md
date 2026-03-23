---
name: "rd-evaluate"
description: "Use for synthesize-stage work in an existing standalone V3 run when the caller already has branch context and wants to close an iteration or continue back to framing."
---

# rd-evaluate

Synthesize-stage skill for the standalone V3 surface.

Maps to `v3.entry.rd_evaluate.rd_evaluate`.

## Tool execution context

- If this skill must drop to direct inspection or primitive tools, run `uv run rdagent-v3-tool ...` from the standalone V3 repo root or from the installed standalone V3 runtime bundle root that owns this skill.
- Do not run direct tools from the caller repo unless the caller repo is that standalone V3 runtime.
- Keep state inspection scoped to the current working repo's canonical V3 state or an explicitly provided state root.

## Trigger requests

- "complete the synthesize stage"
- "resume rd-evaluate"
- "close this branch iteration"
- "decide continue or stop after synthesize"

## When to use

- Complete or replay the synthesize stage for an existing run and branch.
- Use this when you already have `run_id`, `branch_id`, a synthesize summary, synthesize artifact IDs, and a recommendation of `continue` or `stop`.
- Use this when the task is specifically to close a branch iteration or send it back to framing.

## Internal workflows

- Load `workflows/continue.md` when continuing a paused synthesize step with known
  `run_id` and `branch_id`.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` on the agent side when you need to inspect the current run, branch, stage, or artifact state before making a synthesize decision.
- Route to `rd-tool-catalog` on the agent side when you need one specific CLI tool rather than the synthesize-stage wrapper.
- Keep those direct-tool calls in the same standalone V3 repo root or installed runtime bundle root after routing.
- Route to `rd-tool-catalog` when the task is inspection- or primitive-oriented, but keep the operator on the `rd-evaluate` path rather than defaulting to manual tool browsing.

## When not to use

- Do not use this for the default end-to-end orchestration path; use `rd-agent`.
- Do not use this when the branch is still in framing, build, or verify.
- Do not use this as a generic tool selector or CLI reference.
- If blocked, route to: `rd-agent` for full-loop restart, or the correct stage
  skill if the branch is in another stage.
- If state absent, fresh-start only: do not fabricate continuation context;
  route to `rd-agent` for the minimum start contract.

## Failure handling

- If `run_id`, `branch_id`, `summary`, `artifact_ids`, or `recommendation` are missing, inspect current run or branch state, surface the exact missing values, and ask only for the unresolved continuation inputs.
- If the task is inspection- or primitive-oriented after that recovery step, use `rd-tool-catalog` as the agent-side escalation path.
- If the branch belongs to another stage, route to the correct stage skill or back to `rd-agent`.

## Output

- Applies the synthesize-stage transition rules and records whether the next step is `continue` back to framing or `stop`.

## Outcome guide

- `reused`: published synthesize evidence is still valid; honor the existing `recommendation`, then either continue with `rd-propose` for `continue` or close the loop for `stop`.
- `review`: synthesize needs manual review before a safe branch decision can be finalized; surface the review reason and do not claim either `continue` or `stop` is settled.
- `replay`: synthesize needs a fresh publish; replay the step with the recovered continuation payload, then apply the resolved `recommendation`.
- completed with `continue`: the next high-level action is `rd-propose`.
- completed with `stop`: stop the loop and report that no next stage skill should be run.

## Success contract

- Success means the synthesize-stage transition is applied, replayed, reused, or reviewed against canonical V3 state.
- The skill should return a concrete branch outcome: continue back to framing or stop the loop.
