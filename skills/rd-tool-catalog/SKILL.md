---
name: "rd-tool-catalog"
description: "Use for choosing direct standalone V3 CLI tools after deciding a high-level skill boundary is insufficient."
---

# rd-tool-catalog

Decision-oriented skill for the standalone V3 CLI tool surface.

Maps to `v3.entry.tool_catalog` and the `rdagent-v3-tool list` / `rdagent-v3-tool describe` interface.

## Tool execution context

- Run direct CLI tools from the standalone V3 repo root or from the installed standalone V3 runtime bundle root that owns this skill.
- The canonical direct-tool path is:
  - `cd <standalone-v3-root>`
  - `uv run rdagent-v3-tool list`
  - `uv run rdagent-v3-tool describe <tool>`
- Do not run `rdagent-v3-tool` from the caller repo unless the caller repo is that standalone V3 runtime.
- Inspect only the current working repo's canonical V3 state or an explicitly provided state root; if no canonical local state exists, do not search other repos or `HOME`.

## Trigger requests

- "which rd tool should I use"
- "show the CLI tool catalog"
- "describe this direct V3 tool"
- "drop to a primitive tool"

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
- If blocked, route to: `rd-agent` for orchestration, or the correct stage skill
  if the caller knows which stage they need.
- If state absent: this skill does not require persisted V3 state to function;
  it operates on catalog metadata only.

## Failure handling

- If the caller has not yet established that a high-level skill is insufficient, keep them in `rd-agent` or the appropriate stage skill.
- If the request is still too broad after category narrowing, ask one focused follow-up instead of selecting a primitive tool arbitrarily.
- If the caller already knows the exact high-level stage wrapper they need, route back out of the catalog to that skill.

## Reference loading

- Load `references/tool-selection.md` only when you need help mapping a vague request onto `category`, `subcategory`, or a representative direct tool.
- Do not load the reference when the caller already knows the exact tool or when the request should stay in a high-level skill.

## Routing model

- Stay in high-level skills unless they are insufficient for the task.
- If you must drop lower, inspect the catalog and narrow by category first.
- Use `recommended_entrypoint` to decide whether to stay with `rd-agent` or select a direct tool through `rd-tool-catalog`.

## Success contract

- Success means the skill narrows the request to a concrete tool choice or explicitly routes the caller back to the correct high-level skill.
- The final output should identify the selected category, any relevant primitive subcategory, and the recommended entrypoint.
