---
phase: 18
slug: standalone-packaging-and-planning-autonomy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest >=7.4.0` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q` |
| **Full suite command** | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q`
- **After every plan wave:** Run `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | STANDALONE-01 | unit scaffold | `test -f v3/devtools/skill_install.py && rg -n "def install_agent_skills|mode == \"link\"|mode == \"copy\"|\\.codex/skills|\\.claude/skills" v3/devtools/skill_install.py` | `v3/devtools/skill_install.py` ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | STANDALONE-01 | wrapper smoke | `uv run python scripts/install_agent_skills.py --runtime codex --scope local --mode link >/tmp/phase18-install.txt && rg -n "codex|local|link" /tmp/phase18-install.txt` | `scripts/install_agent_skills.py` ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | STANDALONE-01 | unit + smoke | `uv run python -m pytest tests/test_phase18_skill_installation.py -q` | `tests/test_phase18_skill_installation.py` ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 2 | STANDALONE-01, STANDALONE-02 | doc-surface | `rg -n "scripts/install_agent_skills.py --runtime codex --scope local --mode link|uv run rdagent-v3-tool list|Quick verification|Full verification" README.md && ! rg -n "## Continue This Session" README.md` | `README.md` ✅ | ⬜ pending |
| 18-02-02 | 02 | 2 | STANDALONE-02 | continuity docs | `rg -n "Current phase.*18|18-CONTEXT.md|18-RESEARCH.md|18-VALIDATION.md" .planning/STATE.md && rg -n "\\.planning/STATE.md" .planning/V3-EXTRACTION-HANDOFF.md && ! rg -n "docs/context/SESSION-HANDOFF.md|/Users/michael-liang/Code/my-RDagent-V3" .planning/V3-EXTRACTION-HANDOFF.md` | `.planning/STATE.md` ✅ / `.planning/V3-EXTRACTION-HANDOFF.md` ✅ | ⬜ pending |
| 18-02-03 | 02 | 2 | STANDALONE-01, STANDALONE-02 | full regression | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q && uv run lint-imports` | `tests/test_phase18_planning_continuity.py` ❌ W0 / `tests/test_phase18_skill_installation.py` ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase18_skill_installation.py` — stubs for symlink install, rerun idempotence, broken-link repair, and copy fallback
- [ ] `tests/test_phase18_planning_continuity.py` — stubs for README public-only boundary and `.planning/STATE.md` / handoff continuity assertions

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Agent skill visibility in a real Claude/Codex environment | STANDALONE-01 | pytest can validate generated links and paths, but not actual third-party agent UI discovery in this repo sandbox | Install skills into a local or global target, then confirm Claude Code or Codex lists the linked skill names from the target root |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
