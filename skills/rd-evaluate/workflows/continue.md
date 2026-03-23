# Continue contract: rd-evaluate (synthesize)

Use this skill to continue a paused run inside the known synthesize step rather than restarting the entire standalone flow.

The operator-facing job is: continue the current synthesize step with the exact
continuation identifiers and payload, then return the branch decision as
`continue` or `stop`.

Keep the operator at the high-level skill layer unless the agent must inspect
lower-level run, branch, or recovery state to recover missing continuation data.

## Required fields

- `run_id`: the run identifier for the paused standalone V3 run.
- `branch_id`: the branch identifier that owns the current synthesize step.
- `summary`: the current-step summary to publish for this synthesize continuation.
- `artifact_ids`: the current-step artifact identifiers to publish or replay for this synthesize continuation.
- `recommendation`: the extra continuation field for synthesize outcomes, with the exact public values `continue` and `stop`.

## If information is missing

- First inspect current run or branch state instead of asking the operator to browse tools manually.
- Then surface the exact missing values, including which continuation fields are unresolved and which values the agent already recovered from current state.
- Ask the operator only for values that cannot already be derived.
- If the agent still needs a direct inspection or recovery primitive, use `rd-tool-catalog` as an agent-side escalation path and return with the resolved synthesize continuation payload.
