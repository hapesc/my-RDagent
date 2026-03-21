---
name: "rd-tool-catalog"
description: "Decision-oriented skill for selecting direct V3 CLI tools."
---

# rd-tool-catalog

Decision-oriented skill for the standalone V3 CLI tool surface.

Maps to `v3.entry.tool_catalog` and the `rdagent-v3-tool list` / `rdagent-v3-tool describe` interface.

## When to use

- Choose a direct V3 CLI tool after deciding not to stay in a higher-level skill.
- Inspect the catalog metadata for `category`, `subcategory`, and `recommended_entrypoint`.
- Narrow the search space before selecting a specific tool.

## When to route to rd-tool-catalog

- Route here from `rd-agent`, `rd-propose`, `rd-code`, `rd-execute`, or `rd-evaluate` when the task needs a concrete CLI tool rather than a high-level skill.
- Route here when you need to narrow by the top-level categories `orchestration`, `inspection`, and `primitives`.
- Route here when you need the primitive subcategories `branch_lifecycle`, `branch_knowledge`, `branch_selection`, or `memory` to choose one direct tool.

## When not to use

- Do not use this when the high-level skill boundary is sufficient and the caller should stay in `rd-agent` or a stage skill.
- Do not use this as the default path for starting a run.
- Do not use this as a replacement for end-to-end orchestration.

## Routing model

- Stay in high-level skills unless they are insufficient for the task.
- If you must drop lower, inspect the catalog and narrow by category first.
- Use `recommended_entrypoint` to decide whether to stay with `rd-agent` or select a direct tool through `rd-tool-catalog`.
