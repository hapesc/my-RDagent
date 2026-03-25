<purpose>
Continue a paused synthesize step for an existing V3 run. Recover missing fields
from state before asking the operator. Return the branch decision as continue
(back to rd-propose) or stop (end the loop).
</purpose>

<required_reading>
@skills/_shared/references/stage-contract.md
@skills/_shared/references/tool-execution-context.md
</required_reading>

<process>

<step name="validate_fields">
Check required continuation fields: run_id, branch_id, summary, artifact_ids,
recommendation.

If any missing:
1. Run `uv run rdagent-v3-tool rd_run_get` and `uv run rdagent-v3-tool rd_branch_get`
   to inspect current state
2. Derive what can be derived from the response
3. Surface exact missing field names and values already recovered
4. Ask operator ONLY for values that cannot be derived

Recommendation must be exactly "continue" or "stop".

If all present: proceed to next step.
</step>

<step name="check_stage">
Verify branch is actually in the synthesize stage.

If not synthesize:
- framing → route to rd-propose
- build → route to rd-code
- verify → route to rd-execute
- unknown or no active run → route to rd-agent
</step>

<step name="execute_transition">
Apply synthesize-stage transition:

```bash
uv run rdagent-v3-tool rd_stage_publish \
  --run-id "$RUN_ID" \
  --branch-id "$BRANCH_ID" \
  --stage synthesize \
  --summary "$SUMMARY" \
  --artifact-ids "$ARTIFACT_IDS" \
  --recommendation "$RECOMMENDATION"
```

Evaluate result per outcome_guide in SKILL.md:
- reused → honor existing recommendation
- review → surface review reason, STOP (do not claim continue or stop is settled)
- replay → re-publish with recovered payload, then apply resolved recommendation
- error → load @skills/_shared/references/failure-routing.md, follow recovery
</step>

<step name="handoff">
If recommendation is "continue":
- Report: "Synthesize complete. Recommendation: continue. Next skill: rd-propose"
- Branch goes back to framing for the next iteration

If recommendation is "stop":
- Report: "Synthesize complete. Recommendation: stop. Loop ends."
- No next stage skill should be invoked

Include branch_id and artifact summary for continuity in both cases.
</step>

</process>

<success_criteria>
- [ ] All required fields validated or recovered from state
- [ ] Branch confirmed in synthesize stage before transition attempt
- [ ] Transition applied via canonical CLI tool (rd_stage_publish)
- [ ] Outcome matches one of: reused, review, replay, completed
- [ ] Branch decision (continue/stop) is explicit and actionable
</success_criteria>
