---
phase: 24
slug: operator-guidance-and-next-step-ux
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-22
---

# Phase 24 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.x` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest tests/test_phase24_operator_guidance.py -q` |
| **Full suite command** | `uv run python -m pytest tests/test_phase14_stage_skills.py tests/test_phase19_tool_guidance.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase21_public_surface_narrative.py tests/test_phase22_intent_routing.py tests/test_phase23_stage_preflight_integration.py tests/test_v3_tool_cli.py tests/test_phase24_operator_guidance.py tests/test_phase24_stage_next_step_guidance.py -q && uv run lint-imports` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_phase24_operator_guidance.py -q`
- **After every plan wave:** Run `uv run python -m pytest tests/test_phase22_intent_routing.py tests/test_phase23_stage_preflight_integration.py tests/test_v3_tool_cli.py tests/test_phase19_tool_guidance.py tests/test_phase24_operator_guidance.py tests/test_phase24_stage_next_step_guidance.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 0 | GUIDE-05 | unit | `uv run python -m pytest tests/test_phase24_operator_guidance.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 24-01-02 | 01 | 0 | GUIDE-05 | integration | `uv run python -m pytest tests/test_phase22_intent_routing.py tests/test_phase24_operator_guidance.py -q` | ❌ W0 | ⬜ pending |
| 24-02-01 | 02 | 1 | GUIDE-05 | integration | `uv run python -m pytest tests/test_phase23_stage_preflight_integration.py tests/test_phase24_stage_next_step_guidance.py -q` | ❌ W0 | ⬜ pending |
| 24-02-02 | 02 | 1 | GUIDE-05 | integration | `uv run python -m pytest tests/test_phase23_stage_preflight_integration.py tests/test_phase24_stage_next_step_guidance.py -q` | ❌ W0 | ⬜ pending |
| 24-02-03 | 02 | 1 | GUIDE-05 | regression | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase19_tool_guidance.py -q` | ✅ existing | ⬜ pending |
| 24-02-04 | 02 | 1 | GUIDE-05 | regression | `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase21_public_surface_narrative.py tests/test_phase22_intent_routing.py -q` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase24_operator_guidance.py` — focused route-surface and shared-helper coverage for mixed summaries, blocked ordering, selective detail expansion, and canonical projection rules
- [ ] `tests/test_phase24_stage_next_step_guidance.py` — full stage outcome guidance matrix coverage before the full cross-surface wave

*Existing Phase 19, 20, 21, 22, and 23 pytest infrastructure covers the CLI tool surface and public docs once the new Phase 24 test files are added.*

---

## Manual-Only Verifications

All Phase 24 behaviors should be automatable from deterministic fixtures and
file-reading regressions. No manual-only verification is planned.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
