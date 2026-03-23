---
phase: 17
slug: skill-and-cli-surface-terminology-convergence
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-21
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest >=7.4.0` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q` |
| **Full suite command** | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q`
- **After every plan wave:** Run `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| `17-02-01` | 02 | 1 | SURFACE-02 | doc-surface scaffold | `uv run python -m pytest tests/test_phase17_surface_convergence.py -q` | ❌ created by task | ⬜ pending |
| `17-02-02` | 02 | 1 | SURFACE-01, SURFACE-03 | unit/public-surface | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q` | `tests/test_v3_tool_cli.py` ✅ / `tests/test_phase16_tool_surface.py` ✅ / `tests/test_phase17_surface_convergence.py` ✅ after 17-02-01 | ⬜ pending |
| `17-01-01` | 01 | 2 | SURFACE-02, SURFACE-03 | doc/package | `uv run python -m pytest tests/test_phase17_surface_convergence.py -q` | `tests/test_phase17_surface_convergence.py` ✅ | ⬜ pending |
| `17-03-02` | 03 | 3 | SURFACE-01, SURFACE-02, SURFACE-03 | doc-surface final | `uv run python -m pytest tests/test_phase17_surface_convergence.py -q` | `tests/test_phase17_surface_convergence.py` ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all pre-execution needs. Plan `17-02` Task 1 creates the remaining Phase 17 regression scaffold before any later wave depends on it.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Repo-local skill package phrasing remains decision-oriented for agent routing | SURFACE-02, SURFACE-03 | Skill package quality is partially semantic and may not be fully captured by one-line regex checks | Review each `skills/*/SKILL.md` to confirm it states when to use the skill, when to route to `rd-tool-catalog`, and when not to use the skill |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-21
