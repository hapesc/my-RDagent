<purpose>
Continue a paused framing step for an existing V3 run. Recover missing fields
from state before asking the operator. Hand the successful path to rd-code.
</purpose>

<required_reading>
@skills/_shared/references/stage-contract.md
@skills/_shared/references/tool-execution-context.md
</required_reading>

## Required fields

- `run_id`
- `branch_id`
- `summary`
- `artifact_ids`

Use this workflow to continue a paused run rather than restarting it.
Treat `summary` as the current-step summary and `artifact_ids` as the current-step artifact list.

## If information is missing

- inspect current run or branch state first
- surface the exact missing values and any values already recovered
- Ask the operator only for values that cannot already be derived

<process>

<step name="validate_fields">
Check required continuation fields: run_id, branch_id, summary, artifact_ids.

If any missing:
1. Run `uv run rdagent-v3-tool rd_run_get` and `uv run rdagent-v3-tool rd_branch_get`
   to inspect current state
2. Derive what can be derived from the response
3. Surface exact missing field names and values already recovered
4. Ask operator ONLY for values that cannot be derived

If all present: proceed to next step.
</step>

<step name="check_stage">
Verify branch is actually in the framing stage.

If not framing:
- build → route to rd-code
- verify → route to rd-execute
- synthesize → route to rd-evaluate
- unknown or no active run → route to rd-agent
</step>

<step name="execute_transition">
Apply framing-stage transition:

```bash
uv run rdagent-v3-tool rd_stage_publish \
  --run-id "$RUN_ID" \
  --branch-id "$BRANCH_ID" \
  --stage framing \
  --summary "$SUMMARY" \
  --artifact-ids "$ARTIFACT_IDS"
```

Evaluate result per outcome_guide in SKILL.md:
- reused → confirm reuse result, hand to rd-code
- review → surface review reason, STOP (do not claim ready for rd-code)
- replay → re-publish with recovered payload, then hand to rd-code
- error → load @skills/_shared/references/failure-routing.md, follow recovery
</step>

<step name="handoff">
If transition succeeded normally:
- Report: "Framing complete. Next skill: rd-code"
- Include branch_id and artifact summary for continuity
- Do not proceed into build — the operator or rd-agent decides when to invoke rd-code
</step>

</process>

<success_criteria>
- [ ] All required fields validated or recovered from state
- [ ] Branch confirmed in framing stage before transition attempt
- [ ] Transition applied via canonical CLI tool (rd_stage_publish)
- [ ] Outcome matches one of: reused, review, replay, completed
- [ ] Handoff to rd-code is explicit (or blocked with reason)
</success_criteria>
