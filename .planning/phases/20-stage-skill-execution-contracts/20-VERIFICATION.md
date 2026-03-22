---
phase: 20-stage-skill-execution-contracts
verified: 2026-03-22T05:57:49Z
status: passed
score: 8/8 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 7/8
  gaps_closed:
    - "Phase 20 regressions fail if `rd-agent` drops the minimum contract, the pause explanation, or the agent-led missing-field guidance."
    - "Phase 20 continuation regressions substantively lock the four paused-run stage skill contracts."
  gaps_remaining: []
  regressions: []
---

# Phase 20: Stage Skill Execution Contracts Verification Report

**Phase Goal:** Developers can start and continue the standalone stage loop from the skill packages using explicit minimal inputs and default stop/continue semantics.
**Verified:** 2026-03-22T05:57:49Z
**Status:** passed
**Re-verification:** Yes - after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `skills/rd-agent/SKILL.md` names the exact minimum start fields for `rd-agent` instead of only describing them in prose. | ✓ VERIFIED | `skills/rd-agent/SKILL.md` lists `title`, `task_summary`, `scenario_label`, `stage_inputs.framing.summary`, and `stage_inputs.framing.artifact_ids` in both `## Required fields` and `## Minimum start contract`. |
| 2 | `skills/rd-agent/SKILL.md` distinguishes the strict minimum start contract from the recommended multi-branch path. | ✓ VERIFIED | Separate `## Minimum start contract` and `## Recommended multi-branch contract` sections exist, and `branch_hypotheses` is explicitly described as recommended rather than required. |
| 3 | `skills/rd-agent/SKILL.md` explains the default `gated + max_stage_iterations=1` path in plain language as completing the current step and then pausing for review while the next step is prepared. | ✓ VERIFIED | `skills/rd-agent/SKILL.md` includes the literal default string, the human-review pause sentence, the sentence that the next step is prepared but not continued automatically, and the public stop reason `awaiting_operator`; `v3/orchestration/execution_policy.py` and `tests/test_phase14_execution_policy.py` match that behavior. |
| 4 | Phase 20 regressions substantively lock the `rd-agent` start contract, pause explanation, tool-escalation boundary, and agent-led missing-field guidance. | ✓ VERIFIED | `tests/test_phase20_rd_agent_skill_contract.py` is now 81 lines, reads `skills/rd-agent/SKILL.md` directly, and contains seven focused contract assertions; `uv run python -m pytest tests/test_phase14_execution_policy.py tests/test_phase16_rd_agent.py tests/test_phase20_rd_agent_skill_contract.py -q` passed. |
| 5 | Each stage-skill package names the exact continuation identifiers and payload fields needed to continue a paused run. | ✓ VERIFIED | `skills/rd-propose/SKILL.md`, `skills/rd-code/SKILL.md`, `skills/rd-execute/SKILL.md`, and `skills/rd-evaluate/SKILL.md` all document `run_id`, `branch_id`, `summary`, and `artifact_ids`. |
| 6 | All four stage skills share one documented continuation skeleton for `run_id`, `branch_id`, `summary`, and `artifact_ids`. | ✓ VERIFIED | All four skill packages expose the same `## Continue contract`, `## Required fields`, `## If information is missing`, and `## Outcome guide` structure. |
| 7 | `rd-execute` explicitly documents `blocking_reasons`, and `rd-evaluate` explicitly documents `recommendation` with the exact values `continue` and `stop`. | ✓ VERIFIED | `skills/rd-execute/SKILL.md` names `blocking_reasons` as the blocked-path extra field; `skills/rd-evaluate/SKILL.md` names `recommendation` with exact public values `continue` and `stop`; `v3/entry/rd_execute.py` and `v3/entry/rd_evaluate.py` match. |
| 8 | The stage-skill packages tell the agent to inspect current run or branch state and surface missing values instead of pushing the operator into manual tool browsing. | ✓ VERIFIED | All four stage skill docs include the recovery wording and keep `rd-tool-catalog` as an agent-side escalation path; `tests/test_phase20_stage_skill_contracts.py` locks that text directly. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `skills/rd-agent/SKILL.md` | Operator-usable `rd-agent` start contract and plain-language default pause semantics | ✓ VERIFIED | Exists, 108 lines, contains `## Minimum start contract`, `## Recommended multi-branch contract`, and `## Default stop behavior`. |
| `tests/test_phase20_rd_agent_skill_contract.py` | Focused Phase 20 regression coverage for the `rd-agent` skill package | ✓ VERIFIED | Exists, 81 lines, contains `test_rd_agent_skill_names_minimum_start_contract`, and reads the skill file directly. |
| `skills/rd-propose/SKILL.md` | First-step continuation contract anchored to `rd-code` handoff | ✓ VERIFIED | Exists, 77 lines, contains `## Continue contract`, and points successful completion to `rd-code`. |
| `skills/rd-code/SKILL.md` | Build-step continuation contract anchored to `rd-execute` handoff | ✓ VERIFIED | Exists, 77 lines, contains the shared continuation skeleton, and points successful completion to `rd-execute`. |
| `skills/rd-execute/SKILL.md` | Verification continuation contract with blocked-path fields | ✓ VERIFIED | Exists, 80 lines, contains `blocking_reasons`, and distinguishes normal completion from blocked verification. |
| `skills/rd-evaluate/SKILL.md` | Synthesis continuation contract with continue-or-stop decision | ✓ VERIFIED | Exists, 79 lines, contains `recommendation`, `continue`, and `stop`, and maps branch outcomes to the next high-level action. |
| `tests/test_phase20_stage_skill_contracts.py` | Focused Phase 20 regression coverage for the four continuation skill packages | ✓ VERIFIED | Exists, 95 lines, contains `test_stage_skills_share_continuation_skeleton`, and reads all four skill files directly. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `skills/rd-agent/SKILL.md` | `tests/test_phase20_rd_agent_skill_contract.py` | literal contract-string assertions | WIRED | The test file reads the skill doc directly and asserts the minimum contract, default pause semantics, tool-escalation wording, and missing-field recovery language. |
| `skills/rd-agent/SKILL.md` | `v3/contracts/tool_io.py` | exact start-field truth | WIRED | `RunStartRequest` exposes `title`, `task_summary`, `scenario_label`, `execution_mode`, and `max_stage_iterations`; the skill doc names the required subset plus the stage payload fields. |
| `skills/rd-agent/SKILL.md` | `v3/orchestration/execution_policy.py` | plain-language pause semantics anchored to public stop behavior | WIRED | The doc’s `gated + max_stage_iterations=1` and `awaiting_operator` wording aligns with the execution-policy branch that pauses for operator review. |
| `skills/rd-propose/SKILL.md` | `skills/rd-code/SKILL.md` | explicit next high-level action after a successful continuation | WIRED | `rd-propose` outcome guidance sends the normal completion path to `rd-code`. |
| `skills/rd-execute/SKILL.md` | `v3/entry/rd_execute.py` | exact special continuation field for blocked verification | WIRED | Both the skill doc and entrypoint use `blocking_reasons` only for the blocked path. |
| `skills/rd-evaluate/SKILL.md` | `v3/entry/rd_evaluate.py` | exact continue-or-stop recommendation field | WIRED | Both the skill doc and entrypoint use `recommendation` with exact public values `continue` and `stop`. |
| `tests/test_phase20_stage_skill_contracts.py` | `skills/rd-propose/SKILL.md` | shared continuation contract assertions | WIRED | The test file reads all four stage skill docs directly and locks the shared field skeleton, special fields, recovery wording, and outcome handoffs. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| SKILL-01 | 20-01-PLAN.md | Developer can start `rd-agent` from the skill package with an explicit minimal-input contract that names the required run fields and the required stage payload fields. | ✓ SATISFIED | `skills/rd-agent/SKILL.md` documents the exact run fields and `stage_inputs.framing.*`, and `tests/test_phase20_rd_agent_skill_contract.py` locks those strings directly. |
| SKILL-02 | 20-01-PLAN.md | Developer can understand the default `rd-agent` gated behavior, including that `gated + max_stage_iterations=1` pauses after the first completed stage for operator review. | ✓ SATISFIED | `skills/rd-agent/SKILL.md` states the pause semantics, and `v3/orchestration/execution_policy.py` plus `tests/test_phase14_execution_policy.py` confirm `awaiting_operator` pause behavior. |
| SKILL-03 | 20-02-PLAN.md | Developer can continue from a paused `rd-agent` run by following stage-skill guidance that states the exact identifiers and payload fields needed for `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate`. | ✓ SATISFIED | All four stage skill docs expose the shared continuation skeleton, plus `blocking_reasons` and `recommendation` where required; `tests/test_phase20_stage_skill_contracts.py` locks the doc surface. |

No orphaned Phase 20 requirements were found. `20-01-PLAN.md` declares `SKILL-01` and `SKILL-02`, `20-02-PLAN.md` declares `SKILL-03`, and `.planning/REQUIREMENTS.md` maps exactly those three requirements to Phase 20.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | No TODO/FIXME/placeholder or empty-implementation patterns found in the Phase 20 key files. | ℹ️ Info | No phase-owned blocker anti-patterns found. |

### Human Verification Required

None.

### Gaps Summary

All previously recorded Phase 20 gaps are closed. The two regression files that were previously below the plan-declared substantive floor now exceed those thresholds and directly lock the intended skill-contract surface.

One broader referenced regression command still includes a non-Phase-20 failure: `tests/test_phase14_stage_skills.py::test_importlinter_extends_forbidden_imports_to_stage_write_tools` expects `.importlinter` to forbid legacy modules such as `app.control_plane`, `app.query_services`, `app.runtime`, and `core.loop`, but the current `.importlinter` only lists `service_contracts`, `data_models`, and `exploration_manager`. That drift does not contradict the Phase 20 goal, artifacts, or key links, so it is recorded here as external regression noise rather than a Phase 20 blocker.

---

_Verified: 2026-03-22T05:57:49Z_
_Verifier: Claude (gsd-verifier)_
