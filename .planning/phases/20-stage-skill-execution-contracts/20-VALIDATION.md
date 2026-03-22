---
phase: 20
slug: stage-skill-execution-contracts
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-22
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py -q` |
| **Full suite command** | `uv run python -m pytest tests/test_phase14_execution_policy.py tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase16_rd_agent.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py -q`
- **After every plan wave:** Run `uv run python -m pytest tests/test_phase14_execution_policy.py tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase16_rd_agent.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 0 | SKILL-01 | unit/doc-surface | `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py -q` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 0 | SKILL-02 | unit/doc-surface | `uv run python -m pytest tests/test_phase14_execution_policy.py tests/test_phase20_rd_agent_skill_contract.py -q` | ✅/❌ W0 | ⬜ pending |
| 20-02-01 | 02 | 0 | SKILL-03 | unit/doc-surface | `uv run python -m pytest tests/test_phase20_stage_skill_contracts.py -q` | ❌ W0 | ⬜ pending |
| 20-02-02 | 02 | 0 | SKILL-03 | behavior-anchor | `uv run python -m pytest tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase20_stage_skill_contracts.py -q` | ✅/❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase20_rd_agent_skill_contract.py` — lock `rd-agent` minimum-input contract, multi-branch recommendation, and pause wording
- [ ] `tests/test_phase20_stage_skill_contracts.py` — lock shared continuation skeleton, per-skill extras, and missing-field guidance

*Existing infrastructure covers all phase requirements once the two Phase 20 test files are added.*

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
