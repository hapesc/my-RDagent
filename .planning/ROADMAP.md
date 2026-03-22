# Roadmap: my-RDagent-V3

## Overview

This roadmap tracks the active `v1.2 skill-and-tool-guidance-hardening`
milestone. The milestone hardens skill metadata, tool metadata, and public
operator guidance so agents can advance the standalone V3 loop without reading
source code to discover the next valid action.

## Archived Milestones

- ✅ **v1.0 Standalone V3 Baseline** — shipped 2026-03-21
  Archive: `.planning/milestones/v1.0-standalone-v3-baseline.md`
- ✅ **v1.1 Standalone Surface Consolidation** — shipped 2026-03-21
  Archive: `.planning/milestones/v1.1-standalone-surface-consolidation.md`

## Current Milestone

**v1.2 skill-and-tool-guidance-hardening**

**Milestone Goal:** Make the standalone V3 surface executable from skill and
tool guidance alone, with no scope expansion into new orchestration features.

**Coverage:** 8/8 active v1 requirements mapped

## Phases

- [x] **Phase 19: Tool Catalog Operator Guidance** - Add concrete examples,
  routing guidance, and follow-up semantics to the direct V3 CLI tool surface.
- [x] **Phase 20: Stage Skill Execution Contracts** - Make `rd-agent` and the
  stage skills executable from explicit minimal-input and pause/continue
  contracts. (completed 2026-03-22)
- [ ] **Phase 21: Executable Public Surface Narrative** - Lock the guidance
  into README and regression coverage so the standalone pipeline stays
  operator-usable.

## Phase Details

### Phase 19: Tool Catalog Operator Guidance
**Goal**: Developers can inspect a direct V3 CLI tool and know the common-path
request shape, the correct routing layer, and the next action after a
successful result.
**Depends on**: Phase 18
**Requirements**: GUIDE-01, GUIDE-02, GUIDE-03
**Success Criteria** (what must be TRUE):
  1. A developer can inspect a direct V3 CLI tool entry and copy a realistic
     common-path request example without reading the implementation.
  2. A developer can tell from the tool entry when to use the direct tool, when
     not to use it, and which higher-level skill is the preferred route
     instead.
  3. After a successful direct-tool call, including orchestration or gated-stop
     outcomes, a developer can identify the expected follow-up action from the
     tool metadata alone.
**Plans**: 2/2 complete

Plans:
- [x] `19-01-PLAN.md` — Add structured common-path examples and explicit routing boundaries to the direct tool catalog payload. (completed 2026-03-22)
- [x] `19-02-PLAN.md` — Add structured follow-up semantics and regression coverage for next-step operator guidance. (completed 2026-03-22)

### Phase 20: Stage Skill Execution Contracts
**Goal**: Developers can start and continue the standalone stage loop from the
skill packages using explicit minimal inputs and default stop/continue
semantics.
**Depends on**: Phase 19
**Requirements**: SKILL-01, SKILL-02, SKILL-03
**Success Criteria** (what must be TRUE):
  1. A developer can start `rd-agent` from the skill package using a documented
     minimal-input contract that names the required run fields and required
     stage payload fields.
  2. A developer can understand from the skill guidance that
     `gated + max_stage_iterations=1` pauses after the first completed stage
     for operator review.
  3. A developer can continue a paused run with `rd-propose`, `rd-code`,
     `rd-execute`, or `rd-evaluate` by supplying the exact documented
     identifiers and payload fields for the next valid stage action.
**Plans**: 2/2 complete

Plans:
- [x] `20-01-PLAN.md` — Add explicit `rd-agent` start-contract and gated pause guidance. (completed 2026-03-22)
- [x] `20-02-PLAN.md` — Add continuation contracts and regression coverage for `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate`. (completed 2026-03-22)

### Phase 21: Executable Public Surface Narrative
**Goal**: Developers can use the README and regression suite as the stable
public reference for the standalone V3 pipeline start, inspect, and continue
flows.
**Depends on**: Phase 20
**Requirements**: SURFACE-01, SURFACE-02
**Success Criteria** (what must be TRUE):
  1. A developer can read the README and follow a concrete start, inspect, and
     continue path through the standalone V3 pipeline.
  2. The README describes the standalone surface as an executable skill-and-tool
     workflow rather than as a schema catalog that still requires source-code
     spelunking.
  3. Regression tests fail if the public tool catalog or skill packages drift
     away from the required guidance fields, concrete examples, or pipeline
     semantics.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 19. Tool Catalog Operator Guidance | 2/2 | Complete | 2026-03-22 |
| 20. Stage Skill Execution Contracts | 2/2 | Complete   | 2026-03-22 |
| 21. Executable Public Surface Narrative | 0/TBD | Not started | - |

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
