# Intent-first routing and paused-run continuation

## Intent-first routing

- Treat `rd-agent` as the public intent-first entry surface: the user can describe work in plain language without naming a skill first.
- Inspect current persisted run and branch state before deciding whether to start fresh, continue a paused run, or downshift.
- Prefer a paused run when one is clearly active in the current working context.
- Default the user-facing routing reply to four explicit fields:
  - `current_state`
  - `routing_reason`
  - `exact_next_action`
  - `recommended_next_skill`
- Phase 24 may add two optional detail fields when the reply needs a minimum
  executable payload:
  - `next_step_detail`
  - `detail_hint`
- When preflight truth blocks the recommended path, keep `recommended_next_skill` visible and add the blocker plus the repair action rather than pretending the stage is executable.
- Keep the reply concise and operator-facing. The user should not need to infer the next skill from orchestration prose.

## Paused-run continuation preference

- If current state already exposes a paused run, surface the current `run_id`, `branch_id`, and stage, then recommend the matching stage skill explicitly.
- Typical continuation mapping is: `framing -> rd-propose`, `build -> rd-code`, `verify -> rd-execute`, and `synthesize -> rd-evaluate`.
- If canonical preflight fails, the reply should state that the recommended path is blocked, surface one blocker category, and give one repair action before reusing the same continuation skill.
- Starting a new run is the fallback path only when paused work does not dominate the current context.
- Healthy paused runs should stay terse by default and prefer `detail_hint`
  over a full continuation dump.
- Fresh-start replies and blocked replies may include `next_step_detail` as a
  one-line minimum command or skeleton.
