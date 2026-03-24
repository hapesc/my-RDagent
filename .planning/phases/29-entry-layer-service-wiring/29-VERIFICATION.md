---
phase: 29-entry-layer-service-wiring
verified: 2026-03-24T22:14:06+08:00
status: passed
score: 3/3 phase truths verified
---

# Phase 29: Entry-Layer Service Wiring Verification Report

**Phase Goal:** Wire the Phase 27 sharing/finalization services into the public
`rd_agent` entrypoint so holdout finalization, operator guidance, and the
reachable sharing path are available through the production code path.
**Verified:** 2026-03-24T22:14:06+08:00
**Status:** passed
**Verification scope:** executed code, Phase 29 plan/summary artifacts, targeted
Phase 16/20/26/27/28/29 regression suites, and roadmap/requirements traceability

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `rd_agent()` now wires the multi-branch entrypoint with `BranchShareService`, `HoldoutValidationService`, and the correct `MemoryStorePort` implementation instead of leaving those services unreachable from the public entry surface. | ✓ VERIFIED | `v3/entry/rd_agent.py` imports and constructs `BranchShareService`, `HoldoutValidationService`, `MemoryService`, and `MemoryStateStore`; the `rd_agent()` signature now accepts `memory_store`, `holdout_split_port`, and `holdout_evaluation_port`; inside the multi-branch path it constructs `MemoryStateStore` from `state_store._root` when no explicit memory store is injected, rejects missing `holdout_evaluation_port`, and passes both optional services into `MultiBranchService`; `tests/test_phase29_entry_wiring.py` proves `MultiBranchService` receives non-`None` share/holdout services and that `MemoryService` receives a dedicated `MemoryStateStore`. |
| 2 | Public entry responses now surface holdout finalization artifacts truthfully and treat finalization as authoritative: finalization data appears only when holdout finalization actually triggers, and when it does the returned `selected_branch_id` / `recommended_next_step` align with the holdout winner instead of a later convergence fallback. | ✓ VERIFIED | `v3/entry/rd_agent.py` now converts `explore_round.finalization_submission` into `finalization_guidance` via `build_finalization_guidance()` plus `operator_guidance_to_dict()`, skips the convergence payload projection when finalization already fired, returns the holdout winner as `selected_branch_id`, and emits `recommended_next_step="review final submission"`; `tests/test_phase29_entry_wiring.py` verifies triggered finalization, non-triggered finalization, and an end-to-end `rd_agent -> exploration -> holdout -> winner` path whose selected branch matches `finalization_submission["winner_branch_id"]`. |
| 3 | The entry-layer wiring and its public documentation do not regress earlier public orchestration paths: the relevant rd-agent, Phase 20, Phase 26, Phase 27, Phase 28, and Phase 29 regression bundle all pass together. | ✓ VERIFIED | `uv run pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase29_entry_wiring.py tests/test_phase16_rd_agent.py tests/test_phase26_integration.py tests/test_phase27_global_injection.py tests/test_phase27_integration.py tests/test_phase28_integration.py -x -q` passed with `55 passed in 0.72s`, confirming the new entry wiring coexists with prior multi-branch, sharing, and holdout behaviors while keeping the rd-agent skill contract green. |

**Score:** 3/3 phase truths verified

### Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| `P28-HOLDOUT` | ✓ SATISFIED | `v3/entry/rd_agent.py` now constructs `HoldoutValidationService` with `dag_service`, `split_port`, and `evaluation_port`, and passes it into `MultiBranchService`; `tests/test_phase29_entry_wiring.py` verifies the service is injected through the public entry surface; `tests/test_phase28_integration.py` verifies the underlying holdout lifecycle and persistence behavior. |
| `P28-ACTIVATE` | ✓ SATISFIED | `v3/entry/rd_agent.py` now propagates `explore_round.finalization_submission` when finalization triggers and treats that winner as the authoritative public selection; `tests/test_phase29_entry_wiring.py::test_finalization_triggers_through_entry` forces `max_rounds=1` and `tests/test_phase29_entry_wiring.py::test_e2e_rd_agent_to_winner` verifies activation through the public entry path. |
| `P28-SUBMIT` | ✓ SATISFIED | `v3/entry/rd_agent.py` now serializes `explore_round.finalization_submission` into `structuredContent[\"finalization_submission\"]`; `tests/test_phase29_entry_wiring.py` verifies the response includes a winner-bearing finalization submission. |
| `P28-PRESENT` | ✓ SATISFIED | `v3/entry/rd_agent.py` now calls `build_finalization_guidance()` and returns the rendered guidance payload in `structuredContent[\"finalization_guidance\"]`; `tests/test_phase29_entry_wiring.py` and `tests/test_phase28_integration.py::test_operator_guidance_for_finalization` verify the finalization guidance shape and content. |
| `P27-KERNEL` | ✓ SATISFIED | `v3/entry/rd_agent.py` now injects `BranchShareService` into `MultiBranchService`, making the Phase 27 sharing kernel reachable from the public entrypoint; `v3/orchestration/branch_share_service.py` still owns the interaction-kernel-backed sharing logic; `tests/test_phase29_entry_wiring.py` confirms the service injection and callable global-best path, while `tests/test_phase27_global_injection.py` covers the service behavior itself. |
| `P27-INJECT` | ✓ SATISFIED | `v3/entry/rd_agent.py` now passes a live `BranchShareService` into `MultiBranchService`, which uses `identify_global_best()` and `compute_sharing_candidates()` during later rounds; `tests/test_phase29_entry_wiring.py::test_global_best_injection_through_entry` proves the injected service is present and callable through `rd_agent()`, and `tests/test_phase27_global_injection.py` covers the underlying injection behavior. |
| `GUIDE-05` | ✓ SATISFIED | `v3/entry/rd_agent.py` now exposes finalization operator guidance in the public response instead of keeping Phase 28 guidance trapped behind lower-level services; `tests/test_phase29_entry_wiring.py` confirms the response payload includes `current_state` guidance when finalization occurs. |

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `.planning/phases/29-entry-layer-service-wiring/29-01-SUMMARY.md` | Execution summary with task commits, deviations, and post-review closeout | ✓ VERIFIED | Exists and records the original `6aa33b9` / `f11d74e` / `6dd4040` / `ad00f1a` execution chain plus the finalization-first closeout adjustments. |
| `v3/entry/rd_agent.py` | Public entry-layer wiring for share/holdout/finalization services | ✓ VERIFIED | Exists and contains the new imports, injection parameters, service construction, finalization guard, and finalization response projection. |
| `tests/test_phase29_entry_wiring.py` | Entry-level integration proof for holdout/finalization/wiring behavior | ✓ VERIFIED | Exists and passed 9/9 tests in the targeted regression gate, including the finalization-first response check and the explicit missing-`holdout_evaluation_port` contract failure. |
| `README.md` / `skills/rd-agent/*` | Public contract documents mention the structured multi-branch holdout dependency truthfully | ✓ VERIFIED | The README and rd-agent skill docs now distinguish legacy `branch_hypotheses` from structured `hypothesis_specs`, require `holdout_evaluation_port` for the structured path, and describe the finalization-first public response semantics. |

### Automated Checks

| Command | Result | Evidence |
| --- | --- | --- |
| `uv run pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase29_entry_wiring.py tests/test_phase16_rd_agent.py tests/test_phase26_integration.py tests/test_phase27_global_injection.py tests/test_phase27_integration.py tests/test_phase28_integration.py -x -q` | ✓ PASSED | 55/55 tests passed in 0.72s. |
| `git log --oneline --all --grep='29-01' -n 20` | ✓ PASSED | Found the expected Phase 29 task commit chain: `6aa33b9`, `f11d74e`, `6dd4040`, `ad00f1a`. |
| `rg -n "HoldoutValidationService\\(|BranchShareService\\(|MemoryStateStore\\(|build_finalization_guidance\\(|finalization_guidance|finalization_submission|memory_store: MemoryStorePort \\| None = None|holdout_evaluation_port|review final submission" v3/entry/rd_agent.py README.md skills/rd-agent/SKILL.md skills/rd-agent/workflows/start-contract.md -S` | ✓ PASSED | Confirmed the expected entry-layer wiring markers, finalization-first response text, and documented holdout dependency are present in code and public docs. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `v3/entry/rd_agent.py` | `v3/orchestration/branch_share_service.py` | `BranchShareService(...)` constructor injection into `MultiBranchService` | ✓ WIRED | The public entrypoint now creates and passes the share service whenever `hypothesis_specs` and `dag_service` are present. |
| `v3/entry/rd_agent.py` | `v3/orchestration/holdout_validation_service.py` | `HoldoutValidationService(...)` constructor injection into `MultiBranchService` | ✓ WIRED | The entrypoint now provides holdout split/evaluation ports and routes finalization through the existing holdout service. |
| `v3/entry/rd_agent.py` | `v3/orchestration/memory_state_store.py` | `MemoryStateStore(...)` fallback for `MemoryService` | ✓ WIRED | The entrypoint now uses a true `MemoryStorePort` implementation instead of incorrectly reusing the artifact state store. |
| `v3/entry/rd_agent.py` | `v3/orchestration/operator_guidance.py` | `build_finalization_guidance(...)` + `operator_guidance_to_dict(...)` | ✓ WIRED | Finalization guidance now reaches the public `rd_agent` response payload, and the finalization winner now remains authoritative in the returned public selection fields. |

### Human Verification Required

None. The Phase 29 goal is expressed through deterministic service wiring and
public response payloads, and the relevant automated regression bundle is green.

### Remaining Risks

| Risk | Impact | Status |
| --- | --- | --- |
| `rd_agent()` still does not expose an `EmbeddingPort`, so peer-sharing candidate sampling remains dormant even though the share service is now injected. | Phase 29 proves entry wiring and reachable global-best/share-service flow, but not full peer-sharing activation from the public entry surface. | Non-blocking follow-up debt; not a Phase 29 wiring failure. |
| Downstream callers still infer "exploration vs finalization" from payload shape (`finalization_submission is not None`) instead of a dedicated status field. | The public response is now truthful, but callers still need one small convention to distinguish exploration-state and finalization-state payloads. | Non-blocking follow-up enhancement; captured separately as future interface debt. |

### Gaps Summary

No blocking gaps found. Phase 29 achieved its entry-layer wiring goal, exposes
holdout finalization and operator guidance through the public `rd_agent`
surface, and passes the relevant regression bundle without breaking prior
phases.

---

_Verified: 2026-03-24T22:14:06+08:00_
_Verifier: Codex (manual fallback after gsd-verifier callback stall)_
