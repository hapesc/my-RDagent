# Continue contract: rd-code (build)

Use this skill to continue a paused run inside the known build step rather than restarting the full standalone flow.

The operator-facing job is: continue the current build step with the exact
continuation identifiers and payload, then hand the successful path to
`rd-execute`.

Keep the interaction in the stage-skill layer unless the agent must inspect
lower-level run or recovery state to fill in missing continuation details.

## Required fields

- `run_id`: the run identifier for the paused standalone V3 run.
- `branch_id`: the branch identifier that owns the current build step.
- `summary`: the current-step summary to publish for this build continuation.
- `artifact_ids`: the current-step artifact identifiers to publish or replay for this build continuation.

## If information is missing

- First inspect current run or branch state instead of sending the operator to browse tools manually.
- Then surface the exact missing values, including the unresolved field names and any values the agent already recovered from current state.
- Ask the operator only for values that cannot already be derived.
- If a direct inspection or recovery primitive is still required, use `rd-tool-catalog` as an agent-side escalation path and return with the resolved continuation payload.
