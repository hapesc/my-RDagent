---
phase: 21
slug: executable-public-surface-narrative
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-22
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest tests/test_phase21_public_surface_narrative.py tests/test_phase17_surface_convergence.py tests/test_phase18_planning_continuity.py -q` |
| **Full suite command** | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py tests/test_phase19_tool_guidance.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_phase21_public_surface_narrative.py -q && uv run lint-imports` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_phase21_public_surface_narrative.py tests/test_phase17_surface_convergence.py tests/test_phase18_planning_continuity.py -q`
- **After every plan wave:** Run `uv run python -m pytest tests/test_phase21_public_surface_narrative.py tests/test_phase17_surface_convergence.py tests/test_phase18_planning_continuity.py tests/test_phase19_tool_guidance.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_v3_tool_cli.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 0 | SURFACE-01 | unit/doc-surface | `uv run python -m pytest tests/test_phase21_public_surface_narrative.py -q` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 0 | SURFACE-02 | unit/doc-surface integration | `uv run python -m pytest tests/test_phase21_public_surface_narrative.py tests/test_phase17_surface_convergence.py tests/test_phase18_planning_continuity.py tests/test_phase19_tool_guidance.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_v3_tool_cli.py -q` | ❌/✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase21_public_surface_narrative.py` — locks `Start -> Inspect -> Continue` narrative semantics, agent-first framing, multi-branch example plus single-branch fallback note, and README links to real skill/tool surfaces

*Existing infrastructure covers all phase requirements once the Phase 21 README regression file is added.*

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
