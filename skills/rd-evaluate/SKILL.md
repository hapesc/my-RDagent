---
name: "rd-evaluate"
description: "Synthesize-stage skill for the standalone V3 loop."
---

# rd-evaluate

Synthesize-stage skill for the standalone V3 surface.

Maps to `v3.entry.rd_evaluate.rd_evaluate`.

## When to use

- Complete or replay the synthesize stage for an existing run and branch.
- Use this when you already have `run_id`, `branch_id`, a synthesize summary, synthesize artifact IDs, and a recommendation of `continue` or `stop`.
- Use this when the task is specifically to close a branch iteration or send it back to framing.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` when you need to inspect the current run, branch, stage, or artifact state before making a synthesize decision.
- Route to `rd-tool-catalog` when you need one specific CLI tool rather than the synthesize-stage wrapper.
- Route to `rd-tool-catalog` when the task is inspection- or primitive-oriented instead of a stage transition.

## When not to use

- Do not use this for the default end-to-end orchestration path; use `rd-agent`.
- Do not use this when the branch is still in framing, build, or verify.
- Do not use this as a generic tool selector or CLI reference.

## Output

- Applies the synthesize-stage transition rules and records whether the next step is `continue` back to framing or `stop`.
