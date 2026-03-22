# Roadmap: my-RDagent-V3

## Overview

This roadmap tracks the current standalone V3 milestone state. Shipped
milestones are archived under `.planning/milestones/`, and new roadmap work
starts again after `$gsd-new-milestone` defines the next milestone and fresh
requirements.

## Archived Milestones

- ✅ **v1.0 Standalone V3 Baseline** — shipped 2026-03-21
  Archive: `.planning/milestones/v1.0-standalone-v3-baseline.md`
- ✅ **v1.1 Standalone Surface Consolidation** — shipped 2026-03-21
  Archive: `.planning/milestones/v1.1-standalone-surface-consolidation.md`
- ✅ **v1.2 Skill and Tool Guidance Hardening** — shipped 2026-03-22
  Archive: `.planning/milestones/v1.2-ROADMAP.md`

## Current Milestone

No active milestone.

Use `$gsd-new-milestone` to define the next milestone, create fresh
requirements, and reopen the roadmap for new phases.

## Phases

No active phases. Historical phase details for shipped milestones live in
`.planning/milestones/`.

## Progress

| Milestone | Scope | Status | Shipped |
|-----------|-------|--------|---------|
| v1.0 Standalone V3 Baseline | Phases 12-16 | Complete | 2026-03-21 |
| v1.1 Standalone Surface Consolidation | Phases 17-18 | Complete | 2026-03-21 |
| v1.2 Skill and Tool Guidance Hardening | Phases 19-21 | Complete | 2026-03-22 |

## Planning Defaults

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
