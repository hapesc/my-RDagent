---
phase: 25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps
verified: 2026-03-23T05:19:59Z
status: passed
score: 6/6 phase truths verified
---

# Phase 25: Fix QA-Discovered Operator Guidance and Multi-Branch UX Gaps Verification Report

**Phase Goal:** Fix 6 QA-discovered issues and expose multi-branch exploration as the default UX. Change execution_mode default to exploration, auto-generate branch hypotheses in routing guidance, add copy-pasteable skeletons to all guidance paths, materialize next-stage snapshots on completion, unify outcome fields, and rename disposition to recovery_assessment.
**Verified:** 2026-03-23T05:19:59Z
**Status:** passed
**Verification scope:** executed code, all three Phase 25 summaries, and the full repository regression gate

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `route_user_intent` start-new-run guidance now recommends multi-branch exploration and includes auto-generated branch hypotheses. | ✓ VERIFIED | [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py):53-59 defines `_generate_branch_hypotheses`, and [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py):160-187 uses it inside `build_start_new_run_guidance`; [rd_agent.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_agent.py):160-226 routes plain-language start intent through that shared guidance; [test_phase25_multi_branch_ux.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_multi_branch_ux.py):32-68 locks the exploration wording, three hypotheses, and hypothesis-bearing detail payload. |
| 2 | `rd_run_start` now exposes `exploration_mode` and `branch_hypotheses` as public request fields, and `rd_agent` accepts/persists them. | ✓ VERIFIED | [tool_io.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/tool_io.py):24-34 adds `exploration_mode` and `branch_hypotheses` to `RunStartRequest`; [rd_agent.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_agent.py):229-270 accepts and forwards both fields; [run_board_service.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/run_board_service.py):82-93 persists `exploration_mode` onto the run snapshot; [tool_catalog.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py):189-215 shows both fields in the `rd_run_start` example. |
| 3 | All four stage entry surfaces now expose a consistent top-level `outcome` field for every operator-facing path. | ✓ VERIFIED | [rd_propose.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_propose.py):111,144,172,211,249, [rd_code.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_code.py):112,145,173,212,250, [rd_execute.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_execute.py):114,147,175,214,253-281, and [rd_evaluate.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_evaluate.py):112,152,181,227,275 all publish `outcome`; [test_phase25_outcome_consistency.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_outcome_consistency.py):284-378 verifies preflight-blocked, reused, review, replay, blocked, and completed paths. |
| 4 | Every stage guidance path now includes a copy-pasteable `next_step_detail` skeleton and no longer uses `detail_hint`. | ✓ VERIFIED | [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py):71-118 and [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py):190-221 keep `next_step_detail` as the only expansion surface; [test_phase25_guidance_completeness.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_guidance_completeness.py):285-442 verifies all stage paths, paused guidance, renderer behavior, and `detail_hint` rejection. |
| 5 | Stage completion now materializes a `NOT_STARTED` next-stage snapshot and advances `branch.current_stage_key` immediately. | ✓ VERIFIED | [stage_transition_service.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/stage_transition_service.py):24-40 now writes a `NOT_STARTED` next-stage snapshot with preflight-required wording, while [stage_transition_service.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/stage_transition_service.py):57-83 advances `current_stage_key`; [test_phase25_stage_materialization.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_stage_materialization.py):46-88 verifies materialization, final-stage no-op behavior, and deduplication. |
| 6 | Recovery and resume surfaces now use `recovery_assessment` instead of `disposition` across models, services, entries, and tools. | ✓ VERIFIED | [recovery.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/recovery.py):42-54 renames the contract field; [resume_planner.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/resume_planner.py):12-116 propagates the renamed field through `ResumeDecision` and `plan_resume_decision`; [selection_service.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/selection_service.py):60-63, [scoring_service.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/scoring_service.py):39-60, [skill_loop_service.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/skill_loop_service.py):91-103, and [recovery_tools.py](/Users/michael-liang/Code/my-RDagent-V3/v3/tools/recovery_tools.py):18-29 all consume or serialize `recovery_assessment`; [test_phase25_disposition_rename.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_disposition_rename.py):11-98 locks the new field and rejects the old one. |

**Score:** 6/6 phase truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| [25-01-SUMMARY.md](/Users/michael-liang/Code/my-RDagent-V3/.planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-01-SUMMARY.md) | Outcome/guidance contract execution record | ✓ VERIFIED | Exists and records the `8ec470e` / `0d927f9` / `557fe7c` execution chain. |
| [25-02-SUMMARY.md](/Users/michael-liang/Code/my-RDagent-V3/.planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-02-SUMMARY.md) | Recovery rename execution record | ✓ VERIFIED | Exists and records the `46cbb5e` / `cf44837` / `9ea0e26` execution chain. |
| [25-03-SUMMARY.md](/Users/michael-liang/Code/my-RDagent-V3/.planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-03-SUMMARY.md) | Multi-branch UX and stage-materialization execution record | ✓ VERIFIED | Exists and records the `2d93c67` / `4db305c` / `303d5cb` / `7dda42c` task commits. |
| [tool_io.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/tool_io.py) | `RunStartRequest` exploration fields | ✓ VERIFIED | Exists and contains both new request fields at lines 31-33. |
| [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py) | Start/new-run and stage-guidance canonical source | ✓ VERIFIED | Exists and contains both hypothesis generation and the detail-only guidance model. |
| [recovery.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/recovery.py) | Renamed recovery contract | ✓ VERIFIED | Exists and exposes `recovery_assessment` as the public field. |
| [stage_transition_service.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/stage_transition_service.py) | Next-stage materialization logic | ✓ VERIFIED | Exists and contains `StageStatus.NOT_STARTED` plus the preflight-required summary string. |
| [test_phase25_multi_branch_ux.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_multi_branch_ux.py) | Multi-branch UX regression suite | ✓ VERIFIED | Exists and passed 5/5 tests. |
| [test_phase25_stage_materialization.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_stage_materialization.py) | Stage materialization regression suite | ✓ VERIFIED | Exists and passed 3/3 tests. |
| [test_phase25_outcome_consistency.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_outcome_consistency.py) | Outcome consistency regression suite | ✓ VERIFIED | Exists and passed 21/21 tests. |
| [test_phase25_guidance_completeness.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_guidance_completeness.py) | Guidance completeness regression suite | ✓ VERIFIED | Exists and passed 24/24 tests. |
| [test_phase25_disposition_rename.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_disposition_rename.py) | Recovery rename regression suite | ✓ VERIFIED | Exists and passed 5/5 tests. |

### Automated Checks

| Command | Result | Evidence |
| --- | --- | --- |
| `uv run python -m pytest tests/test_phase25_outcome_consistency.py tests/test_phase25_guidance_completeness.py tests/test_phase24_operator_guidance.py tests/test_phase24_stage_next_step_guidance.py -x -q` | ✓ PASSED | 59/59 tests passed during Plan 25-01 verification. |
| `uv run python -m pytest tests/test_phase25_disposition_rename.py tests/test_phase13_v3_tools.py tests/test_phase14_resume_and_reuse.py tests/test_phase16_selection.py tests/test_phase24_stage_next_step_guidance.py -x -q` | ✓ PASSED | 40/40 tests passed during Plan 25-02 verification. |
| `uv run python -m pytest tests/test_phase25_multi_branch_ux.py -x -q` | ✓ PASSED | 5/5 tests passed during Task 1 verification for Plan 25-03. |
| `uv run python -m pytest tests/test_phase25_stage_materialization.py -x -q` | ✓ PASSED | 3/3 tests passed during Task 2 verification for Plan 25-03. |
| `uv run python -m pytest tests/ -x -q` | ✓ PASSED | 221/221 tests passed in the final full regression gate. |
| `node /Users/michael-liang/.codex/get-shit-done/bin/gsd-tools.cjs verify-summary .../25-01-SUMMARY.md` | ✓ PASSED | Summary self-check, created-files, and commit-existence checks passed. |
| `node /Users/michael-liang/.codex/get-shit-done/bin/gsd-tools.cjs verify-summary .../25-02-SUMMARY.md` | ✓ PASSED | Summary self-check, created-files, and commit-existence checks passed. |
| `node /Users/michael-liang/.codex/get-shit-done/bin/gsd-tools.cjs verify-summary .../25-03-SUMMARY.md` | ✓ PASSED | Summary self-check, created-files, and commit-existence checks passed. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py) | [rd_agent.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_agent.py) | `build_start_new_run_guidance` drives the start-new-run route payload | ✓ WIRED | `route_user_intent()` at [rd_agent.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_agent.py):160-226 now projects the exploration-biased guidance from [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py):160-187. |
| [tool_io.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/tool_io.py) | [tool_catalog.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py) | `RunStartRequest` fields surfaced in the `rd_run_start` example | ✓ WIRED | The contract fields at [tool_io.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/tool_io.py):31-33 are mirrored in the tool-spec example at [tool_catalog.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py):199-211. |
| [tool_io.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/tool_io.py) | [rd_agent.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_agent.py) | `rd_agent` accepts and forwards `exploration_mode` / `branch_hypotheses` to `rd_run_start` | ✓ WIRED | [rd_agent.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_agent.py):239-267 forwards the same fields introduced in [tool_io.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/tool_io.py):31-33. |
| [stage_transition_service.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/stage_transition_service.py) | [tests/test_phase25_stage_materialization.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_stage_materialization.py) | `publish_stage_complete()` writes the materialized next-stage snapshot | ✓ WIRED | The materialization logic at [stage_transition_service.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/stage_transition_service.py):24-40 is directly exercised by [test_phase25_stage_materialization.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase25_stage_materialization.py):46-88. |
| [recovery.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/recovery.py) | [resume_planner.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/resume_planner.py) | `RecoveryAssessment.recovery_assessment` feeds `ResumeDecision.recovery_assessment` | ✓ WIRED | [recovery.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/recovery.py):42-54 and [resume_planner.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/resume_planner.py):17-18,36-115 use the renamed field end-to-end. |

## Requirements Coverage

Phase 25 has no separate `REQUIREMENTS.md` rows; the roadmap success criteria are
the verification contract.

| Requirement | Status | Evidence |
| --- | --- | --- |
| `SC-1` | ✓ SATISFIED | Truth 1 verified via start-new-run guidance generation and `tests/test_phase25_multi_branch_ux.py`. |
| `SC-2` | ✓ SATISFIED | Truth 2 verified via `RunStartRequest`, `rd_agent`, and tool-catalog example wiring. |
| `SC-3` | ✓ SATISFIED | Truth 4 verified via shared guidance builder plus `tests/test_phase25_guidance_completeness.py`. |
| `SC-4` | ✓ SATISFIED | Truth 5 verified via `StageTransitionService.publish_stage_complete()` and `tests/test_phase25_stage_materialization.py`. |
| `SC-5` | ✓ SATISFIED | Truth 3 verified via stage-entry `outcome` fields and `tests/test_phase25_outcome_consistency.py`. |
| `SC-6` | ✓ SATISFIED | Truth 6 verified via renamed recovery contracts, services, tools, and `tests/test_phase25_disposition_rename.py`. |

**Coverage:** 6/6 roadmap success criteria satisfied

## Anti-Patterns Found

None. No Phase 25 modified artifact remained placeholder-only, TODO-gated, or
log-only after the final 221-test regression pass.

## Human Verification Required

Resolved. The operator approved the start-new-run multi-branch hypothesis text as acceptable for Phase 25 sign-off.

## Gaps Summary

**No gaps found.** Phase 25 achieved its goal contract and is ready to proceed.

## Verification Metadata

**Verification approach:** Goal-backward using the Phase 25 roadmap success criteria  
**Must-haves source:** ROADMAP.md success criteria + plan summaries  
**Automated checks:** 8 passed, 0 failed  
**Human checks required:** 0  
**Total verification time:** ~6 min

---
*Verified: 2026-03-23T05:19:59Z*
*Verifier: Codex (manual fallback after gsd-verifier callback stall)*
