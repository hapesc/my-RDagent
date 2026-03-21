---
name: "rd-agent"
description: "Default top-level orchestration skill for the standalone V3 loop."
---

# rd-agent

Primary orchestration skill for the standalone V3 surface.

Maps to `v3.entry.rd_agent.rd_agent`.

## When to use

- Start a new V3 run from a task summary and scenario label.
- Run the full high-level loop instead of calling stage skills one by one.
- Use this when you want the default orchestration path across single-branch and multi-branch execution.

## When to route to rd-tool-catalog

- Route to `rd-tool-catalog` when you need to inspect a specific CLI tool or choose a direct primitive.
- Route to `rd-tool-catalog` when you need category-guided tool selection across `orchestration`, `inspection`, and `primitives`.
- Route to `rd-tool-catalog` when the high-level loop boundary is insufficient and you need one concrete `rd_*` CLI tool.

## When not to use

- Do not use this when the caller already knows it only needs one stage entrypoint such as `rd-propose`, `rd-code`, `rd-execute`, or `rd-evaluate`.
- Do not use this when the task is only to inspect existing run, branch, stage, artifact, or memory state.
- Do not use this as a generic CLI catalog browser; use `rd-tool-catalog` for that.

## Output

- Start or continue the V3 orchestration flow through the canonical run and branch contracts.
- Prefer this skill before dropping to lower-level CLI primitives.
