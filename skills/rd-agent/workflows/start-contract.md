# Start contract and default stop behavior

## Minimum start contract

The strict minimum to start `rd-agent` is a run title, a task summary, a scenario label, and the first-step payload. In public field terms, that means `title`, `task_summary`, `scenario_label`, `stage_inputs.framing.summary`, and `stage_inputs.framing.artifact_ids`.

Use this minimum contract when you only need one concrete starting path and do not need the richer multi-branch setup yet. The first-step payload is the current-step summary plus the artifact ids that support it; the first internal step is `framing`, but the operator-facing truth is still the literal field names above.

## Recommended multi-branch contract

The recommended path is still skill-first: start with the minimum contract, then add optional control fields when the task benefits from multiple candidate approaches. In practice that usually means keeping the required fields above, setting any explicit execution controls you need, and adding `branch_hypotheses` so `rd-agent` can open a richer multi-branch path instead of a single branch only.

Example recommended payload shape:

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

Keep the two layers distinct: `branch_hypotheses` is recommended for the richer path, but it is not part of the strict minimum start contract.

## Default stop behavior

The default operator path is `gated + max_stage_iterations=1`. In plain language, `rd-agent` will complete the current step, then pause for human review before continuing. the next step is prepared but is not continued automatically. It still requires preflight before execution.

If you stay on the default path, the public stop reason is `awaiting_operator`. Internally the first step maps to `framing`, but the main operating rule is simpler: one step finishes, the following step is queued up, and the run stops so a human can review before more work happens.

If you switch to a more continuous unattended path, `rd-agent` can advance further before stopping. Use that only when you want fewer review pauses and you are intentionally changing the default safety boundary.
