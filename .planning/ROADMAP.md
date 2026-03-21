# Roadmap: my-RDagent-V3

## Overview

This roadmap governs the standalone V3 repository. The imported `v1.0`
baseline from the upstream clean-split rebuild is complete; the active work now
starts at `v1.1` and focuses on making the standalone repo coherent in its own
terms:

- skill-first entrypoints
- CLI-described tool surface
- self-contained V3 contracts and orchestration
- planning artifacts that no longer assume MCP terminology

## Milestones

- ✅ **v1.0 Standalone V3 Baseline** — shipped 2026-03-21
- 📋 **v1.1 Standalone Surface Consolidation** — current milestone

## Non-Negotiable Principles

1. **No fake transport**
   - A CLI-described tool catalog must not be mislabeled as an MCP product
     surface.

2. **V3 owns orchestration**
   - The standalone repo keeps orchestration, state truth, and skills inside
     V3-owned layers.

3. **Public truth is V3-owned**
   - Public run, branch, stage, recovery, memory, and exploration semantics
     remain first-class V3 contracts.

4. **Skills and CLI tools are the product surface**
   - `/rd-agent`, `/rd-propose`, `/rd-code`, `/rd-execute`, `/rd-evaluate`,
     and `rdagent-v3-tool` are the primary operator surfaces.

5. **Compatibility is auxiliary**
   - `v3.compat.v2` may exist for historical reasons, but it is not the center
     of the product.

## Current Milestone Phases

### Phase 17: Skill and CLI Surface Terminology Convergence
**Goal:** Rename MCP-era surface language into a coherent skill/CLI requirement and documentation model.
**Depends on:** imported v1.0 baseline
**Requirements:** SURFACE-01, SURFACE-02, SURFACE-03
**Plans:** 3/3 plans complete
Plans:
- [x] 17-01-PLAN.md — create the six repo-local public skill packages via `$skill-architect` (completed 2026-03-21)
- [x] 17-02-PLAN.md — add stable catalog classification metadata and lock it in existing CLI tests
- [x] 17-03-PLAN.md — converge README/project narrative and add Phase 17 surface regression coverage (completed 2026-03-21)
**Success Criteria:**
  1. Requirement IDs and descriptions describe the actual skill/CLI surface instead of an MCP framing.
  2. PROJECT, ROADMAP, REQUIREMENTS, README, and test naming all describe the same public surface.
  3. High-level orchestration tools and direct primitives are explained consistently in standalone-repo language.

### Phase 18: Standalone Packaging and Planning Autonomy
**Goal:** Harden the standalone repository so it can continue independent milestone planning without the upstream worktree.
**Depends on:** Phase 17
**Requirements:** STANDALONE-01, STANDALONE-02
**Plans:** 2/2 plans complete
Plans:
- [x] 18-01-PLAN.md — add the repo-local skill installer/linker and lock local/global Claude/Codex install behavior in pytest (completed 2026-03-21)
- [x] 18-02-PLAN.md — split public README from internal planning continuity, clean stale handoff residue, and lock the boundary with doc regressions (completed 2026-03-21)
**Success Criteria:**
  1. The standalone repo has self-contained packaging, installation, and validation guidance.
  2. The standalone repo’s `.planning/` tree is sufficient to continue GSD sessions and milestone evolution locally.

## Archived Baseline

The imported upstream baseline is now historical context inside this repo.

- Archive: `.planning/milestones/v1.0-standalone-v3-baseline.md`
- Archived requirements: `.planning/milestones/v1.0-standalone-v3-baseline-REQUIREMENTS.md`

## Progress

| Phase | Milestone | Status | Notes |
|-------|-----------|--------|-------|
| v1.0 Standalone V3 Baseline | 12-16 | Complete | archived baseline imported from upstream |
| 17. Skill and CLI Surface Terminology Convergence | 3/3 | Complete   | 2026-03-21 |
| 18. Standalone Packaging and Planning Autonomy | 2/2 | Complete    | 2026-03-21 |

## Notes

This roadmap treats the imported `v1.0` baseline as shipped history and starts
new standalone planning from the first repo-native milestone.
