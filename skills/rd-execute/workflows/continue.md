<purpose>
Continue a paused verify step for an existing V3 run. Recover missing fields
from state before asking the operator. Hand the successful path to rd-evaluate,
or publish explicit blocking reasons.
</purpose>

<required_reading>
@skills/_shared/references/stage-contract.md
@skills/_shared/references/tool-execution-context.md
</required_reading>

<process>

<step name="validate_fields">
Check required continuation fields: run_id, branch_id, summary, artifact_ids.
Also check optional field: blocking_reasons.

If any required field is missing:
1. Run `uv run rdagent-v3-tool rd_run_get` and `uv run rdagent-v3-tool rd_branch_get`
   to inspect current state
2. Derive what can be derived from the response
3. Surface exact missing field names and values already recovered
4. Ask operator ONLY for values that cannot be derived

If the blocked path is required but blocking_reasons is unresolved after
inspection, ask only for the blocking reasons that cannot be derived from
current verification state.

If all present: proceed to next step.
</step>

<step name="check_stage">
Verify branch is actually in the verify stage.

If not verify:
- framing → route to rd-propose
- build → route to rd-code
- synthesize → route to rd-evaluate
- unknown or no active run → route to rd-agent
</step>

<step name="execute_transition">
Apply verify-stage transition:

```bash
uv run rdagent-v3-tool rd_stage_publish \
  --run-id "$RUN_ID" \
  --branch-id "$BRANCH_ID" \
  --stage verify \
  --summary "$SUMMARY" \
  --artifact-ids "$ARTIFACT_IDS"
```

If blocking_reasons provided, include `--blocking-reasons "$BLOCKING_REASONS"`.

Evaluate result per outcome_guide in SKILL.md:
- reused → confirm reuse result, hand to rd-evaluate
- review → surface review reason, STOP
- replay → re-publish with recovered payload, then hand to rd-evaluate
- blocked → publish blocking reasons, keep branch out of rd-evaluate handoff
- error → load @skills/_shared/references/failure-routing.md, follow recovery
</step>

<step name="handoff">
If transition succeeded normally (not blocked):
- Report: "Verify complete. Next skill: rd-evaluate"
- Include branch_id and artifact summary for continuity

If blocked:
- Report: "Verify blocked" with explicit blocking reasons
- Tell operator what must be resolved before verification can continue
- Do not hand off to rd-evaluate
</step>

</process>

<success_criteria>
- [ ] All required fields validated or recovered from state
- [ ] Branch confirmed in verify stage before transition attempt
- [ ] Transition applied via canonical CLI tool (rd_stage_publish)
- [ ] Outcome matches one of: reused, review, replay, blocked, completed
- [ ] Handoff to rd-evaluate is explicit, OR blocking reasons are explicit
</success_criteria>
