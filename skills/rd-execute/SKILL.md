---
name: "rd-execute"
description: "Verify-stage skill for the standalone V3 loop."
---

# rd-execute

Verify-stage skill for the standalone V3 surface.

Maps to `v3.entry.rd_execute.rd_execute`.

## When to use

- Complete, replay, or block the verify stage for an existing run and branch.
- Use this when you already have `run_id`, `branch_id`, a verify summary, and verify artifact IDs.
- Use this when the task is specifically to move a branch from verify toward synthesize or to record blocking reasons.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` when you need direct inspection of stage state, recovery state, or a verification-related primitive.
- Route to `rd-tool-catalog` when you need to select a specific `inspection` or `primitives` tool instead of using the verify-stage wrapper.
- Route to `rd-tool-catalog` when the high-level stage boundary is insufficient for the debugging or inspection task at hand.

## When not to use

- Do not use this to start the overall workflow; use `rd-agent` first for the default orchestration path.
- Do not use this for framing, build, or synthesize ownership when the branch is in another stage.
- Do not use this as a general-purpose catalog interface.

## Output

- Applies verify-stage transitions and records either completion or blocking reasons before the synthesize stage.
