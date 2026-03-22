# Roadmap: my-RDagent-V3

## Overview

This roadmap now tracks the active `v1.3 pipeline-experience-hardening`
milestone. The milestone improves how rdagent guides users through the V3 loop:
intent routing, early preflight, truthful state transitions, and concise
operator-facing next-step guidance.

## Archived Milestones

- ✅ **v1.0 Standalone V3 Baseline** — shipped 2026-03-21
  Archive: `.planning/milestones/v1.0-standalone-v3-baseline.md`
- ✅ **v1.1 Standalone Surface Consolidation** — shipped 2026-03-21
  Archive: `.planning/milestones/v1.1-standalone-surface-consolidation.md`
- ✅ **v1.2 Skill and Tool Guidance Hardening** — shipped 2026-03-22
  Archive: `.planning/milestones/v1.2-ROADMAP.md`

## Current Milestone

**v1.3 pipeline-experience-hardening**

**Milestone Goal:** Make the rdagent pipeline behave more like an operator
assistant than an exposed state machine by improving routing, preflight, and
state-aware guidance.

**Coverage:** 7/7 active v1 requirements mapped

## Phases

- [ ] **Phase 22: Intent Routing and Continuation Control** - Route plain
  language user intent to the correct start, continue, inspect, or downshift
  path without requiring the user to choose a skill first.
- [ ] **Phase 23: Preflight and State Truth Hardening** - Fail early on
  runtime/data/state blockers and ensure user-visible stage claims match
  persisted state artifacts.
- [ ] **Phase 24: Operator Guidance and Next-Step UX** - Add a concise
  state-aware “what next?” surface that explains current state, reason, and
  exact next action.

## Phase Details

### Phase 22: Intent Routing and Continuation Control
**Goal**: Users can describe work in plain language and have the pipeline pick
the right high-level path, especially when paused work already exists.
**Depends on**: Phase 21
**Requirements**: ROUTE-01, ROUTE-02
**Success Criteria** (what must be TRUE):
  1. A user can describe the work they want done without choosing a skill name
     first, and the pipeline routes to start, continue, inspect, or downshift
     based on intent.
  2. When paused work exists, the pipeline surfaces the current run/stage and
     recommends the next valid skill instead of defaulting to a new run.
  3. Common continuation flows no longer require the user to reason about raw
     stage mechanics before taking the next action.
**Plans**: TBD

### Phase 23: Preflight and State Truth Hardening
**Goal**: Stage execution surfaces environment and state blockers early and
keeps user-visible status claims aligned with persisted artifacts.
**Depends on**: Phase 22
**Requirements**: PREFLIGHT-01, PREFLIGHT-02, STATE-01, STATE-02
**Success Criteria** (what must be TRUE):
  1. Before stage execution advances state, the pipeline checks runtime and
     dependency prerequisites and reports exact missing pieces with fix
     guidance.
  2. Before a stage consumes data or artifacts, the pipeline checks required
     files and snapshots and blocks early with a precise reason if something is
     missing.
  3. User-visible claims such as “next stage ready” and verification outcomes
     are backed by persisted snapshots and current handoff artifacts.
**Plans**: TBD

### Phase 24: Operator Guidance and Next-Step UX
**Goal**: Users can reliably ask what to do next and receive a concise,
truthful, state-aware answer.
**Depends on**: Phase 23
**Requirements**: GUIDE-05
**Success Criteria** (what must be TRUE):
  1. Users can ask what to do next and receive the current state, the reason
     for the recommendation, and the exact next action.
  2. Default responses reduce orchestration jargon and expose deeper mechanics
     only when needed.
  3. The next-step surface stays aligned with the real persisted state and the
     public skill/tool surfaces.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 22. Intent Routing and Continuation Control | 0/TBD | Not started | - |
| 23. Preflight and State Truth Hardening | 0/TBD | Not started | - |
| 24. Operator Guidance and Next-Step UX | 0/TBD | Not started | - |

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
