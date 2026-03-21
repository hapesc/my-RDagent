---
name: "rd-code"
description: "Build-stage skill for the standalone V3 loop."
---

# rd-code

Build-stage skill for the standalone V3 surface.

Maps to `v3.entry.rd_code.rd_code`.

## When to use

- Complete or replay the build stage for an existing run and branch.
- Use this when you already have `run_id`, `branch_id`, a build summary, and build artifact IDs.
- Use this when the task is specifically to advance a branch from build toward verify.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` when you need direct inspection of build-stage state, artifacts, or recovery decisions.
- Route to `rd-tool-catalog` when you need one concrete primitive tool instead of the build-stage wrapper.
- Route to `rd-tool-catalog` when the task is better served by category-guided CLI tool selection than by a stage transition.

## When not to use

- Do not use this to orchestrate the full V3 loop; use `rd-agent` for that.
- Do not use this when the work belongs to framing, verify, or synthesize rather than build.
- Do not use this as a passive catalog or documentation surface.

## Output

- Applies the build-stage transition rules and prepares the branch for `rd-execute` when appropriate.
