# Stage Contract: Shared Rules for rd-propose, rd-code, rd-execute, rd-evaluate

All four stage skills share the rules below. Load this reference once and apply
it alongside the stage-specific SKILL.md and workflow.

## Routing constraints

- Do not use a stage skill to start the overall V3 loop; use `rd-agent`.
- Do not use a stage skill when the branch is in a different stage; route to the
  correct stage skill instead.
- Do not use a stage skill as a generic catalog or documentation surface.
- If blocked, route to `rd-agent` for full-loop restart, or to the correct stage
  skill if the branch belongs to another stage.
- If state is absent: do not fabricate continuation context; route to `rd-agent`
  for the minimum start contract.

## When to route to rd-tool-catalog

- Route when you need direct inspection of run, branch, stage, artifact, or
  recovery state before or around the current stage.
- Route when you need one specific CLI primitive instead of the stage wrapper.
- Keep direct-tool calls in the same standalone V3 repo root or installed runtime
  bundle root after routing.
- Do not make manual tool browsing the default operator path; keep the operator on
  the stage-skill continuation whenever possible.

## Failure handling (generic)

1. If `run_id`, `branch_id`, `summary`, or `artifact_ids` are missing, inspect
   current run or branch state first.
2. Surface exact missing field names and any values already recovered.
3. Ask the operator only for values that cannot be derived from state.
4. If the task is inspection- or primitive-oriented after recovery, use
   `rd-tool-catalog` as an agent-side escalation path.
5. If the branch belongs to another stage, route to the correct stage skill or
   back to `rd-agent`.

## Success contract (generic)

- Success means the stage transition is applied, replayed, reused, reviewed, or
  (for verify) blocked against canonical V3 state.
- The skill should leave the branch ready for the next stage skill when the
  transition completes normally, or return explicit blocking reasons.
