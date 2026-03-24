<purpose>
Intent-first routing surface. Parse plain-language input, inspect persisted
state, and dispatch to the correct stage skill or start path. Dispatcher only —
never executes stage logic directly.
</purpose>

<required_reading>
@skills/_shared/references/failure-routing.md
@skills/_shared/references/output-conventions.md
</required_reading>

<process>

<step name="inspect_state">
Check for existing persisted V3 state:

```bash
uv run rdagent-v3-tool rd_run_get 2>/dev/null
```

Track: has_active_run, current_stage, run_id, branch_id.
If the command fails or returns empty, mark has_active_run = false.
</step>

<step name="detect_paused_run">
If has_active_run is true, prefer continuing the paused run over starting fresh.

Determine the current stage and map to the continuation skill:
- framing → rd-propose
- build → rd-code
- verify → rd-execute
- synthesize → rd-evaluate

Surface the current run_id, branch_id, and stage in the routing reply.
</step>

<step name="route">
Apply routing rules (first match):

| Condition | Route to |
|-----------|----------|
| Active run, paused in framing | rd-propose --continue |
| Active run, paused in build | rd-code --continue |
| Active run, paused in verify | rd-execute --continue |
| Active run, paused in synthesize | rd-evaluate --continue |
| No active run + start fields provided | start-contract workflow |
| No active run + no fields | ask for minimum start contract |
| Inspection-only request | rd-tool-catalog |

Starting a new run is the fallback only when paused work does not dominate
the current context.
</step>

<step name="preflight_check">
Before dispatching, verify the recommended path is actually executable:

If preflight blocks the route (missing state, corrupted data, etc.):
- Keep recommended_next_skill visible in reply
- Add the specific blocker description
- Add one concrete repair action
- Do NOT pretend the stage is executable
</step>

<step name="reply">
Return structured routing reply per output-conventions.md:

- current_state: brief description of persisted state
- routing_reason: why this route was chosen
- exact_next_action: the concrete next action
- recommended_next_skill: skill name to use next

For healthy paused runs: prefer detail_hint (terse).
For fresh-start or blocked paths: include next_step_detail (one-line skeleton).
</step>

</process>

<success_criteria>
- [ ] Persisted state inspected before routing decision
- [ ] Paused run preferred over fresh start when active
- [ ] Routing reply contains all 4 required fields (current_state, routing_reason, exact_next_action, recommended_next_skill)
- [ ] Blocked paths include explicit repair action
- [ ] No stage logic executed directly — dispatch only
</success_criteria>
