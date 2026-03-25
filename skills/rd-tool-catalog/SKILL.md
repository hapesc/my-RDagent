---
name: "rd-tool-catalog"
description: "Choose direct standalone V3 CLI tools when a high-level skill boundary is insufficient."
argument-hint: "<tool name> | --list | --category <orchestration|inspection|primitives>"
allowed-tools:
  - Read
  - Bash
---

<codex_skill_adapter>
## Invocation
- Claude Code: `rd-tool-catalog` skill
- Codex: `$rd-tool-catalog`
- Treat text after skill mention as arguments.
</codex_skill_adapter>

<objective>
Decision-oriented skill for the standalone V3 CLI tool surface. Narrows a vague
request to a concrete tool choice or routes back to the correct high-level skill.

Maps to `rd_agent.entry.tool_catalog` and the `rdagent-tool list` / `describe` interface.
</objective>

<execution_context>
@skills/rd-tool-catalog/references/tool-selection.md
@skills/_shared/references/tool-execution-context.md
</execution_context>

<routing_model>
1. Stay in high-level skills unless they are insufficient
2. If dropping lower, inspect catalog and narrow by category first
3. Use recommended_entrypoint to decide rd-agent vs direct tool
4. Do not force a direct tool choice when the caller really wants rd-agent or
   a stage skill
</routing_model>

<process>
1. If caller has not established that a high-level skill is insufficient, route
   back to rd-agent or the appropriate stage skill
2. Narrow by top-level category: orchestration, inspection, primitives
3. If primitives, narrow by subcategory: branch_lifecycle, branch_knowledge,
   branch_selection, memory
4. Select the concrete tool

CLI commands:
```bash
uv run rdagent-tool list
uv run rdagent-tool describe <tool>
```
</process>

<success_contract>
Success means the skill narrows the request to a concrete tool choice or
explicitly routes the caller back to the correct high-level skill. The final
output identifies the selected category, any relevant subcategory, and the
recommended entrypoint.
</success_contract>
