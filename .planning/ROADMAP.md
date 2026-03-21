# Roadmap: my-RDagent-V3

## Overview

This roadmap tracks only the currently active standalone milestone. Completed
milestones are archived under `.planning/milestones/` so the working roadmap
stays small and planning context does not keep growing.

## Archived Milestones

- ✅ **v1.0 Standalone V3 Baseline** — shipped 2026-03-21
  Archive: `.planning/milestones/v1.0-standalone-v3-baseline.md`
- ✅ **v1.1 Standalone Surface Consolidation** — shipped 2026-03-21
  Archive: `.planning/milestones/v1.1-standalone-surface-consolidation.md`

## Current Milestone

No active milestone.

Start the next cycle with `$gsd-new-milestone`, which will define fresh
requirements and write a new active roadmap.

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
