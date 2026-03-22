---
phase: 19
slug: tool-catalog-operator-guidance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest >=7.4.0` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q` |
| **Full suite command** | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q`
- **After every plan wave:** Run `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | GUIDE-01 | unit/public-surface | `uv run python -m pytest tests/test_phase19_tool_guidance.py -q` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | GUIDE-02 | unit/public-surface | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase19_tool_guidance.py -q` | ❌ W0 | ⬜ pending |
| 19-02-01 | 02 | 1 | GUIDE-03 | unit/public-surface | `uv run python -m pytest tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase19_tool_guidance.py` — focused public-surface regression coverage for examples, routing guidance, and follow-up semantics
- [ ] Existing tool-surface tests updated to assert non-empty guidance fields for representative tools

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `uv run rdagent-v3-tool describe rd_run_start` remains easy to read with the added guidance payload | GUIDE-01, GUIDE-02, GUIDE-03 | Human readability of enriched JSON is hard to score from pytest alone | Run the command, inspect that example, routing, and follow-up fields are present and concise |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
