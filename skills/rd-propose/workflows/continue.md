# Continue contract: rd-propose (framing)

Use this skill to continue a paused run inside one known step, not to restart
the whole standalone flow.

The operator-facing job is: continue the current framing step with the exact
continuation identifiers and payload, then hand off the successful path to
`rd-code`.

Keep the interaction at the high-level skill layer unless the agent must inspect
lower-level state to recover missing continuation details.

## Required fields

- `run_id`: the run identifier for the paused standalone V3 run.
- `branch_id`: the branch identifier that owns the current framing step.
- `summary`: the current-step summary to publish for this framing continuation.
- `artifact_ids`: the current-step artifact identifiers to publish or replay for this framing continuation.

## If information is missing

- First inspect current run or branch state instead of asking the operator to browse tools manually.
- Then surface the exact missing values, including which field names are still absent and which values the agent already derived from current state.
- Ask the operator only for values that cannot already be derived.
- If the agent still needs a direct inspection or recovery primitive, use `rd-tool-catalog` as an agent-side escalation path and return with the resolved continuation fields.
