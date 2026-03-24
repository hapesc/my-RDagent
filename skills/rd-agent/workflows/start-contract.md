<purpose>
Define the start contract and default stop behavior for rd-agent. Used when
intent routing determines a fresh run is needed.
</purpose>

<process>

<step name="minimum_contract">
The strict minimum to start rd-agent:

Required fields:
- title (string)
- task_summary (string)
- scenario_label (string)
- stage_inputs.framing.summary (string)
- stage_inputs.framing.artifact_ids (list)

If any field is missing, surface exactly which fields are needed and provide a
one-line skeleton example. Do not guess or fabricate values.
</step>

<step name="recommended_contract">
For richer multi-branch execution, add optional fields:

- initial_branch_label: label for the first branch
- execution_mode: "gated" (default) or continuous
- max_stage_iterations: number of stage cycles before auto-stop (default: 1)
- branch_hypotheses: list of candidate approach labels for multi-branch

Example payload shape:
```text
title="Skill contract hardening"
task_summary="Drive the standalone loop for the operator-guidance phase."
scenario_label="research"
stage_inputs.framing.summary="Framing is complete with a concrete execution plan."
stage_inputs.framing.artifact_ids=["artifact-plan-001"]
initial_branch_label="primary"
execution_mode="gated"
max_stage_iterations=1
branch_hypotheses=["primary", "lighter-doc-pass", "regression-first"]
```

branch_hypotheses is recommended for the richer path but is NOT part of the
strict minimum.
</step>

<step name="default_stop">
Default operator path: gated + max_stage_iterations=1.

Behavior:
1. Complete the current step
2. Pause for human review
3. Next step is prepared but NOT continued automatically
4. Public stop reason: awaiting_operator

To switch to continuous unattended path: operator must explicitly change the
safety boundary. Use that only when fewer review pauses are intentional.
</step>

</process>

<success_criteria>
- [ ] All minimum contract fields present before run start
- [ ] Optional fields clearly separated from required
- [ ] Default stop behavior is gated with human review
- [ ] Payload shape example is concrete and copyable
</success_criteria>
