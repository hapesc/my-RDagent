---
phase: 23
slug: preflight-and-state-truth-hardening
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-22
---

# Phase 23 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.x` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest tests/test_phase23_preflight_service.py -q` |
| **Full suite command** | `uv run python -m pytest tests/test_phase14_execution_policy.py tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase16_rd_agent.py tests/test_phase22_intent_routing.py tests/test_phase23_preflight_service.py tests/test_phase23_stage_preflight_integration.py -q && uv run lint-imports` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_phase23_preflight_service.py -q`
- **After every plan wave:** Run `uv run python -m pytest tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase22_intent_routing.py tests/test_phase23_preflight_service.py tests/test_phase23_stage_preflight_integration.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 0 | PREFLIGHT-01, PREFLIGHT-02 | unit | `uv run python -m pytest tests/test_phase23_preflight_service.py -q` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 0 | STATE-02 | unit | `uv run python -m pytest tests/test_phase23_preflight_service.py -q` | ❌ W0 | ⬜ pending |
| 23-02-01 | 02 | 1 | STATE-01, PREFLIGHT-02 | integration | `uv run python -m pytest tests/test_phase22_intent_routing.py tests/test_phase23_stage_preflight_integration.py -q` | ❌ W0 | ⬜ pending |
| 23-02-02 | 02 | 1 | PREFLIGHT-01, STATE-01, STATE-02 | integration | `uv run python -m pytest tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase16_rd_agent.py tests/test_phase22_intent_routing.py tests/test_phase23_preflight_service.py tests/test_phase23_stage_preflight_integration.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase23_preflight_service.py` - focused unit coverage for runtime, dependency, artifact, state, and recovery blockers
- [ ] `tests/test_phase23_stage_preflight_integration.py` - routing/stage-entry truth regressions

*Existing pytest and lint infrastructure already cover the rest of the phase once the Phase 23 test files are added.*

---

## Manual-Only Verifications

All Phase 23 behaviors should be automatable from deterministic repo fixtures
and file-reading regressions. No manual-only verification is planned.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
