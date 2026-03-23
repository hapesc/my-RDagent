# Continue contract: rd-execute (verify)

Use this skill to continue a paused run inside the known verification step rather than restarting the whole standalone flow.

The operator-facing job is: continue the current verify step with the exact
continuation identifiers and payload, then either hand a successful path to
`rd-evaluate` or publish blocked verification with explicit blocking reasons.

Keep the operator on the high-level skill path unless the agent must inspect
lower-level run, stage, or recovery state to fill in missing continuation data.

## Required fields

- `run_id`: the run identifier for the paused standalone V3 run.
- `branch_id`: the branch identifier that owns the current verify step.
- `summary`: the current-step summary to publish for this verify continuation.
- `artifact_ids`: the current-step artifact identifiers to publish or replay for this verify continuation.
- `blocking_reasons`: the extra continuation field for the blocked verification path; provide it only when the verification step must stop as blocked, and leave it absent or empty for normal completion.

## If information is missing

- First inspect current run or branch state instead of asking the operator to browse tools manually.
- Then surface the exact missing values, including which continuation fields are unresolved and which values the agent already recovered from current state.
- Ask the operator only for values that cannot already be derived.
- If the agent still needs a direct inspection or recovery primitive, use `rd-tool-catalog` as an agent-side escalation path and come back with the resolved verification payload or blocking reasons.
- If the blocked path is required but `blocking_reasons` is still unresolved after inspection, ask only for the blocking reasons that cannot be derived from current verification state.
