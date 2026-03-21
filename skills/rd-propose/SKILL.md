---
name: "rd-propose"
description: "Framing-stage skill for the standalone V3 loop."
---

# rd-propose

Framing-stage skill for the standalone V3 surface.

Maps to `v3.entry.rd_propose.rd_propose`.

## When to use

- Complete or replay the framing stage for an existing run and branch.
- Use this when you already have `run_id`, `branch_id`, a framing summary, and framing artifact IDs.
- Use this when the task is specifically to move a branch from framing toward build.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` when you need direct inspection of run, branch, stage, artifact, or recovery state before or around framing.
- Route to `rd-tool-catalog` when you need a specific CLI primitive instead of the stage entrypoint.
- Route to `rd-tool-catalog` when you need to choose among `inspection` and `primitives` tools rather than staying in the framing stage flow.

## When not to use

- Do not use this to start a new end-to-end workflow; use `rd-agent` for the default orchestration path.
- Do not use this when the branch is already in build, verify, or synthesize and the task belongs to a later stage.
- Do not use this as a general tool discovery surface.

## Output

- Applies the framing-stage transition rules and prepares the branch for `rd-code` when appropriate.
