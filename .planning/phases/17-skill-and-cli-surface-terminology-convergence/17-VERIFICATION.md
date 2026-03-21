---
phase: 17-skill-and-cli-surface-terminology-convergence
verified: 2026-03-21T10:06:12Z
status: passed
score: 3/3 must-haves verified
---

# Phase 17: Skill and CLI Surface Terminology Convergence Verification Report

**Phase Goal:** Rename MCP-era surface language into a coherent skill/CLI requirement and documentation model.  
**Verified:** 2026-03-21T10:06:12Z  
**Status:** passed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Requirement IDs and descriptions describe the actual skill/CLI surface instead of an MCP framing. | ✓ VERIFIED | `.planning/REQUIREMENTS.md` marks `SURFACE-01`, `SURFACE-02`, and `SURFACE-03` complete and uses `MCP-framed catalog wording` instead of registry/server wording; `tests/test_phase17_surface_convergence.py` reads the requirements file directly and passes in the full regression suite. |
| 2 | PROJECT, ROADMAP, REQUIREMENTS, README, and test naming all describe the same public surface. | ✓ VERIFIED | `README.md` states the repo ships `skills plus CLI tools`, leads with `rd-agent`, stages `rd-propose -> rd-code -> rd-execute -> rd-evaluate`, and presents `rd-tool-catalog` plus `rdagent-v3-tool`; `.planning/PROJECT.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` all use the same skill/CLI framing; `tests/test_phase17_surface_convergence.py` locks those strings and passes. |
| 3 | High-level orchestration tools and direct primitives are explained consistently in standalone-repo language. | ✓ VERIFIED | `skills/rd-agent/SKILL.md` declares the default orchestration path and explicit routing to `rd-tool-catalog`; `skills/rd-tool-catalog/SKILL.md` narrows by `orchestration`, `inspection`, and `primitives`; `v3/entry/tool_catalog.py` emits `category`, `subcategory`, and `recommended_entrypoint`; `tests/test_v3_tool_cli.py` and `tests/test_phase16_tool_surface.py` verify the payload shape and representative category assignments. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `README.md` | Public skills-first and CLI-downshift narrative | ✓ EXISTS + SUBSTANTIVE | 204 lines; includes `rd-agent`, `rd-propose`, `rd-code`, `rd-execute`, `rd-evaluate`, `rd-tool-catalog`, `rdagent-v3-tool list`, `rdagent-v3-tool describe`, and `$skill-architect`. |
| `skills/rd-agent/SKILL.md` and `skills/rd-tool-catalog/SKILL.md` | Real public skill packages with routing boundaries | ✓ EXISTS + SUBSTANTIVE | Both files exist, exceed 30 lines, and contain `When to use`, `When to route to rd-tool-catalog`, and `When not to use`. |
| `skills/rd-propose/SKILL.md`, `skills/rd-code/SKILL.md`, `skills/rd-execute/SKILL.md`, `skills/rd-evaluate/SKILL.md` | Stage-specific skill packages mapped to `v3.entry` | ✓ EXISTS + SUBSTANTIVE | All four files exist, exceed 30 lines, reference their exact `v3.entry` module mappings, and define routing boundaries. |
| `v3/entry/tool_catalog.py` | Stable classification and routing metadata source of truth | ✓ EXISTS + SUBSTANTIVE | Defines `ToolCategory`, `ToolSubcategory`, and `RecommendedEntrypoint`, and emits `category`, `subcategory`, and `recommended_entrypoint` from `_catalog_entry`. |
| `tests/test_phase17_surface_convergence.py` | Direct doc-surface regression | ✓ EXISTS + SUBSTANTIVE | 59 lines; reads `README.md`, `.planning/PROJECT.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` directly and asserts the final surface strings. |
| `tests/test_v3_tool_cli.py` and `tests/test_phase16_tool_surface.py` | CLI metadata regression coverage | ✓ EXISTS + SUBSTANTIVE | Both files assert `category`, `subcategory`, and `recommended_entrypoint`, including `orchestration`, `inspection`, `primitives`, and stable primitive subcategories. |

**Artifacts:** 6/6 verified

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `README.md` | `skills/*/SKILL.md` | explicit skill package references | ✓ WIRED | README cites `skills/rd-agent/SKILL.md`, `skills/rd-propose/SKILL.md`, `skills/rd-code/SKILL.md`, `skills/rd-execute/SKILL.md`, `skills/rd-evaluate/SKILL.md`, and `skills/rd-tool-catalog/SKILL.md`. |
| `tests/test_phase17_surface_convergence.py` | `README.md` | direct file reads and string assertions | ✓ WIRED | The test file constructs `README = REPO_ROOT / "README.md"` and asserts final strings such as `rd-agent`, `rd-tool-catalog`, and `$skill-architect`. |
| `tests/test_phase17_surface_convergence.py` | `.planning/REQUIREMENTS.md` | direct file reads and requirement assertions | ✓ WIRED | The test file constructs `REQUIREMENTS = REPO_ROOT / ".planning" / "REQUIREMENTS.md"` and asserts `SURFACE-01`, `SURFACE-02`, and `SURFACE-03`. |
| `v3/entry/tool_catalog.py` | `tests/test_v3_tool_cli.py` | list/describe payload assertions | ✓ WIRED | The tests assert `category`, `subcategory`, and `recommended_entrypoint` from the JSON payloads emitted by the CLI entrypoint. |
| `v3/entry/tool_catalog.py` | `tests/test_phase16_tool_surface.py` | representative category and subcategory assertions | ✓ WIRED | The test verifies `rd_explore_round`, `rd_artifact_list`, `rd_branch_fork`, `rd_branch_share_assess`, `rd_branch_select_next`, and `rd_memory_promote` against the structured catalog metadata. |

**Wiring:** 5/5 connections verified

## Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| `SURFACE-01`: Developer can discover the complete V3 CLI tool catalog through CLI-described commands rather than MCP-framed catalog wording. | ✓ SATISFIED | - |
| `SURFACE-02`: Developer can understand the public V3 surface as skills plus CLI tools consistently across README, ROADMAP, PROJECT, and tests. | ✓ SATISFIED | - |
| `SURFACE-03`: Developer can distinguish high-level orchestration commands from direct primitive tools in the standalone V3 surface. | ✓ SATISFIED | - |

**Coverage:** 3/3 requirements satisfied

## Anti-Patterns Found

None — the scan over `README.md`, `skills/*/SKILL.md`, `tests/test_phase17_surface_convergence.py`, `tests/test_v3_tool_cli.py`, `tests/test_phase16_tool_surface.py`, `v3/entry/tool_catalog.py`, and `.planning/REQUIREMENTS.md` found no `TODO`/`FIXME` markers, placeholders, or empty-return stubs relevant to the phase goal.

## Human Verification Required

None — this phase is documentation, skill packaging, and machine-readable catalog metadata. All phase-goal evidence was verified programmatically.

## Gaps Summary

**No gaps found.** Phase goal achieved. Ready to proceed.

## Verification Metadata

**Verification approach:** Goal-backward, derived from the Phase 17 roadmap goal and success criteria because automated frontmatter extraction did not yield plan-level must_haves for this repo.  
**Must-haves source:** Derived from ROADMAP.md goal and Phase 17 success criteria, cross-checked against plan summaries and the executed codebase.  
**Automated checks:** 34 passed, 0 failed  
**Human checks required:** 0  
**Total verification time:** 1 min

---
*Verified: 2026-03-21T10:06:12Z*  
*Verifier: Codex*
