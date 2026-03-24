# Output Conventions

## Routing replies (rd-agent)

When routing plain-language intent, return these four fields:
- `current_state`: brief description of persisted state
- `routing_reason`: why this route was chosen
- `exact_next_action`: the concrete next action
- `recommended_next_skill`: skill name to use next

Optional fields for blocked or fresh-start paths:
- `next_step_detail`: one-line minimum command or skeleton
- `detail_hint`: terse note for healthy continuation (no full dump)

## Stage transition replies

When a stage transition completes, report:
- Outcome: one of `reused`, `review`, `replay`, `blocked` (verify only), or
  `completed`
- Next skill: the explicit next stage skill name
- Continuity data: `branch_id` and any artifact summary

## Blocked paths

When a recommended path is blocked:
- Keep `recommended_next_skill` visible
- Add the blocker description and one repair action
- Do NOT pretend the stage is executable
