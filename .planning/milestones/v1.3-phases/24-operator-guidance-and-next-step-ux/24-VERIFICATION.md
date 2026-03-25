---
phase: 24-operator-guidance-and-next-step-ux
verified: 2026-03-22T15:10:00Z
status: passed
score: 3/3 phase truths verified
---

# Phase 24: Operator Guidance and Next-Step UX Verification Report

**Phase Goal:** Users can reliably ask what to do next and receive a concise,
truthful, state-aware answer.
**Verified:** 2026-03-22T15:10:00Z
**Status:** passed
**Verification scope:** executed code, plan summaries, and automated regression gates

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Top-level “what next?” routing is now human-first, minimally executable, and still grounded in canonical identifiers plus persisted-state truth. | ✓ VERIFIED | [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py):9-25 defines the canonical stage mapping and detail-expansion hint; [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py):42-50 and [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py):136-170 generate the minimum start skeleton and paused-run detail behavior; [rd_agent.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_agent.py):159-225 projects the shared guidance source into the existing Phase 22 route payload; [test_phase24_operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase24_operator_guidance.py):61-133 locks human-first summaries, repair-first ordering, minimum start detail, and helper projection. |
| 2 | Stage outcomes and resume wording now use the same current-state / reason / next-action guidance shape instead of drifting into per-entrypoint prose. | ✓ VERIFIED | [resume_planner.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/resume_planner.py):36-184 now renders every resume decision through the shared three-part message shape; [rd_propose.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_propose.py):117-275, [rd_code.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_code.py):118-276, [rd_execute.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_execute.py):120-309, and [rd_evaluate.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_evaluate.py):118-302 all emit nested `operator_guidance` payloads plus shared rendered text; [test_phase24_stage_next_step_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase24_stage_next_step_guidance.py):137-356 proves completed, blocked, continue, stop, and resume paths all follow that shape. |
| 3 | The public next-step surface now stays aligned across high-level skills, direct-tool follow-up semantics, and public docs. | ✓ VERIFIED | [tool_catalog.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py):190-236 and [tool_catalog.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py):421-492 align `follow_up.next_action` with the shared stage-skill vocabulary; [README.md](/Users/michael-liang/Code/my-RDagent-V3/README.md):75-135 documents one-line minimum command or skeleton expansion plus terse healthy routes; [rd-agent skill](/Users/michael-liang/Code/my-RDagent-V3/skills/rd-agent/SKILL.md):31-55 and [rd-agent skill](/Users/michael-liang/Code/my-RDagent-V3/skills/rd-agent/SKILL.md):132-140 document `next_step_detail` / `detail_hint`; [test_phase19_tool_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase19_tool_guidance.py):42-76 and [test_v3_tool_cli.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_v3_tool_cli.py):33-55 lock the direct-tool surface. |

**Score:** 3/3 phase truths verified

### Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| `GUIDE-05` | ✓ SATISFIED | [rd_agent.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/rd_agent.py):159-225 now returns human-first route guidance with `next_step_detail` and `detail_hint`; [test_phase24_operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase24_operator_guidance.py):61-133 verifies current state, reason, exact next action, minimum start detail, and selective expansion; [test_phase24_stage_next_step_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase24_stage_next_step_guidance.py):137-356 verifies that stage outcomes and resume wording keep the same concise operator shape; [README.md](/Users/michael-liang/Code/my-RDagent-V3/README.md):75-135 and [skills/rd-agent/SKILL.md](/Users/michael-liang/Code/my-RDagent-V3/skills/rd-agent/SKILL.md):31-55,132-140 keep the public docs aligned with the runtime behavior. |

No uncovered Phase 24 requirements were found.

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| [24-01-SUMMARY.md](/Users/michael-liang/Code/my-RDagent-V3/.planning/phases/24-operator-guidance-and-next-step-ux/24-01-SUMMARY.md) | Route-guidance execution summary | ✓ VERIFIED | Exists and records the RED/feat commits `86ac39e` and `ebb82ef`. |
| [24-02-SUMMARY.md](/Users/michael-liang/Code/my-RDagent-V3/.planning/phases/24-operator-guidance-and-next-step-ux/24-02-SUMMARY.md) | Cross-surface alignment execution summary | ✓ VERIFIED | Exists and records the test/feat/feat/docs commits `0eefd82`, `95dbab4`, `39110dd`, and `1b928bb`. |
| [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/contracts/operator_guidance.py) | Shared Phase 24 guidance contract | ✓ VERIFIED | Exists and contains the exact Phase 24 guidance fields. |
| [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py) | Shared mapping, renderer, and projection logic | ✓ VERIFIED | Exists and contains `STAGE_TO_NEXT_SKILL`, `render_operator_guidance_text`, and projection helpers. |
| [test_phase24_operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase24_operator_guidance.py) | Route/helper regression suite | ✓ VERIFIED | Exists and passed 6/6 tests. |
| [test_phase24_stage_next_step_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase24_stage_next_step_guidance.py) | Stage outcome matrix regression suite | ✓ VERIFIED | Exists and passed 8/8 tests. |

### Automated Checks

| Command | Result | Evidence |
| --- | --- | --- |
| `uv run python -m pytest tests/test_phase22_intent_routing.py tests/test_phase24_operator_guidance.py -q` | ✓ PASSED | 10/10 tests passed during Plan 24-01 execution. |
| `uv run python -m pytest tests/test_phase23_stage_preflight_integration.py tests/test_phase24_stage_next_step_guidance.py -q` | ✓ PASSED | 12/12 tests passed during the stage-guidance integration gate. |
| `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase19_tool_guidance.py -q` | ✓ PASSED | 10/10 tests passed during the direct-tool follow-up alignment gate. |
| `uv run python -m pytest tests/test_phase14_stage_skills.py tests/test_phase19_tool_guidance.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase21_public_surface_narrative.py tests/test_phase22_intent_routing.py tests/test_phase23_stage_preflight_integration.py tests/test_v3_tool_cli.py tests/test_phase24_operator_guidance.py tests/test_phase24_stage_next_step_guidance.py -q` | ✓ PASSED | 59/59 tests passed in the final full regression gate. |
| `rg -n "operator_guidance|render_operator_guidance_text|Current state:|Reason:|Next action:|next_step_detail|detail_hint" ...` | ✓ PASSED | Shared stage/runtime/doc markers are present across resume logic, stage entrypoints, docs, and tests. |
| `rg -n "follow_up|next_entrypoint|next_action" v3/entry/tool_catalog.py tests/test_v3_tool_cli.py tests/test_phase19_tool_guidance.py` | ✓ PASSED | Direct-tool follow-up fields and assertions are present and aligned. |
| `uv run lint-imports` | ⚠ NOT CLEAN | Fails with `Invalid forbidden module app.runtime: subpackages of external packages are not valid.` This appears to be a pre-existing `.importlinter` configuration issue rather than a Phase 24 regression. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `v3/orchestration/operator_guidance.py` | `tests/test_phase24_operator_guidance.py` | route guidance builder proofs for mapping, text rendering, and detail expansion | ✓ WIRED | [operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/operator_guidance.py):9-109 and [test_phase24_operator_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase24_operator_guidance.py):111-133 agree on `STAGE_TO_NEXT_SKILL`, the three-part renderer, and detail expansion behavior. |
| `v3/orchestration/resume_planner.py` | `tests/test_phase24_stage_next_step_guidance.py` | shared resume decisions now feed the same operator-facing answer shape used by stage entrypoints | ✓ WIRED | [resume_planner.py](/Users/michael-liang/Code/my-RDagent-V3/v3/orchestration/resume_planner.py):36-184 and [test_phase24_stage_next_step_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase24_stage_next_step_guidance.py):323-356 both enforce `Current state:` / `Reason:` / `Next action:` messages. |
| `v3/entry/tool_catalog.py` | `tests/test_phase19_tool_guidance.py` | direct tool follow-up semantics stay aligned with the shared Phase 24 next-step vocabulary | ✓ WIRED | [tool_catalog.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py):212-217 and [tool_catalog.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py):446-492 now reference the same stage-skill vocabulary asserted in [test_phase19_tool_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase19_tool_guidance.py):42-76. |
| `README.md` | `skills/rd-agent/SKILL.md` | public docs and skill contract both explain selective detail expansion and minimum next-step payloads | ✓ WIRED | [README.md](/Users/michael-liang/Code/my-RDagent-V3/README.md):79-95,132-135 and [skills/rd-agent/SKILL.md](/Users/michael-liang/Code/my-RDagent-V3/skills/rd-agent/SKILL.md):39-55,137-140 both document `next_step_detail`, `detail_hint`, and one-line minimum detail behavior. |

### Human Verification Required

None. The Phase 24 goal is fully expressed through deterministic routing
payloads, shared stage-outcome guidance payloads, direct-tool metadata, and
file-reading public-surface regressions.

### Remaining Risks

| Risk | Impact | Status |
| --- | --- | --- |
| `.importlinter` still contains an invalid `app.runtime` forbidden-module configuration for external-package mode. | Full repository validation still has one non-Phase-24 red light even though all relevant pytest gates are green. | Known pre-existing tooling debt; non-blocking for Phase 24 correctness, but should be cleaned up separately. |
| The downshift route (`high_level_boundary_sufficient=False`) still uses a local route payload instead of the shared guidance projection helper. | That branch remains truthful, but it is less normalized than the main paused/new-run paths. | Acceptable for this phase because the main user-visible “what next?” paths and the direct-tool surface are aligned; worth revisiting in a later cleanup if more downshift UX work lands. |

### Gaps Summary

No blocking gaps found. Phase 24 achieved its runtime and public-surface goal
and is ready for phase completion tracking.

---

_Verified: 2026-03-22T15:10:00Z_
_Verifier: Codex (manual fallback after gsd-verifier callback stall)_
