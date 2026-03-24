# Failure routing and missing-field recovery

## Failure handling

- If the caller is missing inputs, inspect current run or branch state first,
  surface the exact missing values you can already derive, and ask the operator
  only for the values that still cannot be derived.
- If the caller is missing the inputs needed to start or continue the
  orchestration flow, do not invent them and do not send the operator to browse
  tools manually.
- If the task turns out to be stage-specific rather than full-loop orchestration,
  route to the corresponding stage skill.
- If the task is inspection- or primitive-only, use `rd-tool-catalog` as an
  agent-side escalation path instead of forcing the orchestration wrapper.

## If information is missing

- Inspect current run or branch state before asking for more input.
- Surface the exact missing values, not a vague request for "more context."
- Only ask the operator for values that cannot already be derived from the
  existing run, branch, or artifact state.
- If the missing information proves the task is really stage-specific, route to
  the corresponding stage skill instead of stretching `rd-agent` past its
  boundary.
