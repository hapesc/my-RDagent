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

**Coverage:** 7/7 active v1 requirements mapped + 4 new phases for multi-branch convergence

## Phases

- [x] **Phase 22: Intent Routing and Continuation Control** - Route plain (completed 2026-03-22)
  language user intent to the correct start, continue, inspect, or downshift
  path without requiring the user to choose a skill first.
- [x] **Phase 23: Preflight and State Truth Hardening** - Fail early on (completed 2026-03-22)
  runtime/data/state blockers and ensure user-visible stage claims match
  persisted state artifacts.
- [x] **Phase 24: Operator Guidance and Next-Step UX** - Add a concise (completed 2026-03-22)
  state-aware "what next?" surface that explains current state, reason, and
  exact next action.
- [x] **Phase 25: Fix QA-discovered operator guidance and multi-branch UX gaps** - (completed 2026-03-23)
  Fix 6 QA issues and expose multi-branch exploration as the default UX.
- [x] **Phase 26: Adaptive DAG path management with SelectParents and dynamic pruning** - (completed 2026-03-23)
  First layer of R&D-Agent convergence: DAG diversity, parent selection, pruning.
- [x] **Phase 27: Cross-branch communication and multi-trace solution merge** - (completed 2026-03-24)
  Layers 2-3: global best injection, probabilistic exchange, unified merge.
- [ ] **Phase 28: Aggregated validation with holdout calibration and standardized ranking** -
  Layer 4: holdout re-evaluation, standardized ranking, final submission.

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
  3. User-visible claims such as "next stage ready" and verification outcomes
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
| 22. Intent Routing and Continuation Control | 1/1 | Complete    | 2026-03-22 |
| 23. Preflight and State Truth Hardening | 2/2 | Complete    | 2026-03-22 |
| 24. Operator Guidance and Next-Step UX | 2/2 | Complete    | 2026-03-22 |
| 25. Fix QA-discovered operator guidance and multi-branch UX gaps | 3/3 | Complete   | 2026-03-23 |
| 26. Adaptive DAG path management | 6/6 | Complete | 2026-03-23 |
| 27. Cross-branch communication and multi-trace merge | 5/5 | Complete   | 2026-03-24 |
| 28. Aggregated validation with holdout calibration | 0/0 | Not started | — |

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

### Phase 25: Fix QA-discovered operator guidance and multi-branch UX gaps
**Goal**: Fix 6 QA-discovered issues and expose multi-branch exploration as
the default UX. Change execution_mode default to exploration, auto-generate
branch hypotheses in routing guidance, add copy-pasteable skeletons to all
guidance paths, materialize next-stage snapshots on completion, unify outcome
fields, and rename disposition to recovery_assessment.
**Depends on**: Phase 24
**Requirements**: QA findings from Codex-driven end-to-end testing
**Success Criteria** (what must be TRUE):
  1. route_user_intent start_new_run guidance includes auto-generated branch
     hypotheses and recommends multi-branch exploration by default.
  2. rd_run_start schema exposes exploration_mode and branch_hypotheses.
  3. All stage entry guidance paths include a copy-pasteable next_step_detail
     skeleton (no more selective-detail / detail_hint pattern).
  4. Stage completion materializes a NOT_STARTED next-stage snapshot and
     updates branch.current_stage_key.
  5. All 4 stage entries expose a consistent outcome field in structuredContent.
  6. decision.disposition is renamed to decision.recovery_assessment across
     all surfaces.
**Plans:** 3/3 plans complete
Plans:
- [x] 25-01-PLAN.md — Outcome consistency + guidance completeness + detail_hint removal (SC-3, SC-5)
- [x] 25-02-PLAN.md — Disposition to recovery_assessment rename across all surfaces (SC-6)
- [x] 25-03-PLAN.md — Multi-branch UX defaults + stage materialization (SC-1, SC-2, SC-4)

### Phase 26: Adaptive DAG path management with SelectParents and dynamic pruning
**Goal**: Implement the first layer of the R&D-Agent convergence mechanism:
adaptive directed acyclic graph path management that maximizes first-layer
diversity, selects parent nodes based on validation scores / generalization /
overfitting risk, and dynamically prunes underperforming sub-paths.
**Depends on**: Phase 25
**Requirements**: P26-DAG, P26-SELECT, P26-PRUNE, P26-DIVERSITY, P26-ROUND, P26-SCORE
**Success Criteria** (what must be TRUE):
  1. MultiBranchService supports SelectParents logic that picks the most
     promising nodes based on branch scores and generalization metrics.
  2. Branches can be dynamically pruned when their exploration_priority drops
     below a configurable threshold.
  3. First-layer diversity is maximized by ensuring initial hypotheses span
     distinct approach categories.
**Plans:** 6/6 plans executed and verified
Plans:
- [x] 26-01-PLAN.md — All Phase 26 contracts, model extensions, algorithms, and DAG CRUD (P26-DAG, P26-SCORE, P26-ROUND, P26-DIVERSITY)
- [x] 26-02-PLAN.md — DAGService + SelectParentsService + ScoringService extension (P26-DAG, P26-SELECT, P26-SCORE)
- [x] 26-03-PLAN.md — Multi-signal pruning algorithm + BranchPruneService upgrade (P26-PRUNE)
- [x] 26-04-PLAN.md — MultiBranchService integration: auto-prune, round tracking, DAG nodes, HypothesisSpec wiring (P26-ROUND, P26-DIVERSITY, P26-SELECT, P26-PRUNE)
- [x] 26-05-PLAN.md — Gap closure: rd_agent outward contract, mixed-input validation, legacy compatibility, and prune-skip invariants
- [x] 26-06-PLAN.md — Gap closure: structured-path diversity semantics and later-round DAG parent linkage
**Verification note:** `$gsd-verify-work 26` rerun passed on 2026-03-23. Phase 26 is now complete and Phase 27 can build on the verified DAG/diversity contracts.

### Phase 27: Cross-branch communication and multi-trace solution merge
**Goal**: Implement layers 2-3 of the R&D-Agent convergence mechanism:
cross-branch collaborative communication (global best injection +
probabilistic sampling exchange) and multi-trace solution merge (identify
complementary components + synthesize unified solution from multiple branches).
**Depends on**: Phase 26
**Requirements**: P27-KERNEL, P27-INJECT, P27-COMPONENT, P27-SELECT, P27-PRUNE4, P27-MERGE, P27-E2E
**Success Criteria** (what must be TRUE):
  1. Global best artifacts and techniques can be injected into any branch's
     context during its next iteration.
  2. Probabilistic sampling kernel enables branches to discover and adopt
     successful patterns from topically similar high-scoring peers.
  3. A merge stage can identify complementary components across branches and
     synthesize a unified solution that outperforms any single branch.
**Canonical refs:** `26-CONTEXT.md §deferred`, `v3/contracts/exploration.py` (DAGEdgeSnapshot)
**Phase 26 decisions that constrain Phase 27:**
  - DAG layer provides SHARED and MERGED edge types (defined in Phase 26 but
    unused). Phase 27 activates these edges for cross-branch communication and
    merge operations.
  - SelectParents complementarity signal: Phase 26 reserves the field in the
    three-dimensional signal model. Phase 27 must implement the computation
    (component complementarity for merge-stage parent selection).
  - Merge-stage parent selection: Phase 26 falls back to K=1 when budget_ratio
    >= 0.8. Phase 27 implements multiple complementary parent selection.
  - Dynamic pruning complementarity preservation: Phase 26 prunes on signals
    1-3 only. Phase 27 adds signal 4 (protect branches with unique components
    valuable for merge).
  - Interaction kernel negative feedback for diversity enforcement is deferred
    from Phase 26.
  - DAGService graph traversal (get_ancestors, get_descendants, get_frontier)
    is the infrastructure Phase 27 should use for cross-branch discovery.
**Plans**: TBD

### Phase 28: Aggregated validation with holdout calibration and standardized ranking
**Goal**: Implement layer 4 of the R&D-Agent convergence mechanism: aggregated
validation that prevents overfitting to the primary validation set through
holdout calibration, parallel re-evaluation, and standardized ranking for
final submission selection.
**Depends on**: Phase 27
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. Top candidate solutions from all exploration branches are collected into
     a candidate set for final evaluation.
  2. A synthetic holdout set (90-10 split) is created and candidates are
     re-evaluated in isolated environments.
  3. Standardized ranking produces a single best submission based on holdout
     performance, not primary validation set performance.
**Canonical refs:** `26-CONTEXT.md §deferred`, `v3/contracts/exploration.py` (DAGNodeSnapshot)
**Phase 26 decisions that constrain Phase 28:**
  - DAG frontier traversal (`DAGService.get_frontier`) is the mechanism for
    collecting top candidates from all exploration branches.
  - BranchScore now carries `generalization_gap` and `overfitting_risk` —
    Phase 28 should use these signals for holdout calibration and overfitting
    prevention rather than inventing separate metrics.
  - NodeMetrics on DAGNodeSnapshot store per-node validation_score,
    generalization_gap, overfitting_risk, diversity_score — Phase 28 reads
    these directly for ranking.
  - `max_rounds` on RunSnapshot defines the exploration budget; Phase 28
    activates after `current_round >= max_rounds`.
**Plans**: TBD
