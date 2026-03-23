# Requirements: my-RDagent-V3

**Defined:** 2026-03-22
**Core Value:** A developer can use a self-contained V3 skill and CLI surface on
top of V3-owned contracts and orchestration, without reading source code just
to discover how to start, pause, resume, or continue the loop.

## v1 Requirements

### Intent Routing

- [x] **ROUTE-01**: User can describe work in plain language and the pipeline
  chooses the correct high-level path: start a new run, continue a paused run,
  inspect state, or downshift only when necessary.
- [x] **ROUTE-02**: When paused work already exists, the pipeline surfaces the
  current run and stage and recommends the next valid skill instead of opening
  a new run by default.

### Preflight and Environment

- [x] **PREFLIGHT-01**: Before stage execution advances state, the pipeline
  checks required runtime versions and Python dependencies and reports exact
  missing prerequisites with concrete fix guidance.
- [x] **PREFLIGHT-02**: Before a stage consumes data, artifacts, or state, the
  pipeline checks that required files and snapshots exist and blocks early with
  an explicit reason when they do not.

### State Truth

- [x] **STATE-01**: User-visible claims such as "next stage ready" are backed
  by persisted stage snapshots and current handoff artifacts rather than surface
  prose alone.
- [x] **STATE-02**: Verification can distinguish "results exist" from
  "environment is reproducible" and records that difference as a first-class
  blocked or passed state.

### Operator Guidance

- [x] **GUIDE-05**: User can ask what to do next and receive a concise answer
  that states the current state, the reason for the recommendation, and the
  exact next action without requiring orchestration jargon.

## v1.3 Convergence Mechanism Requirements

### DAG Topology

- [ ] **P26-DAG**: Independent DAG topology layer with DAGNodeSnapshot,
  DAGEdgeSnapshot, NodeMetrics contracts, DAGService graph operations, and
  StateStorePort CRUD methods. Tracks parent-child relationships separately
  from branch lifecycle model.

### Parent Selection

- [ ] **P26-SELECT**: SelectParentsService answers "which past nodes should
  feed context into a new iteration" using a three-dimensional signal model:
  core quality (validation score, generalization gap, overfitting risk),
  strategic planning (budget-aware diversity weight via cosine decay), and
  complementarity (reserved for Phase 27). Dynamic parent count: K=3 early,
  K=1 iteration, K=1 merge (Phase 26 fallback).

### Dynamic Pruning

- [ ] **P26-PRUNE**: Multi-signal dynamic pruning with time-aware cosine-decay
  threshold, generalization stability protection, anti-overfitting preferential
  pruning, and min_active_branches=2 safety constraint. Triggers automatically
  after each exploration round.

### First-Layer Diversity

- [ ] **P26-DIVERSITY**: HypothesisSpec with ApproachCategory enum enforces
  category uniqueness constraint (at most 1 branch per category in first layer)
  and computes diversity_score as Shannon entropy of category distribution.

### Round Tracking

- [ ] **P26-ROUND**: RunBoardSnapshot carries current_round and max_rounds.
  MultiBranchService.run_exploration_round increments current_round after each
  round. budget_ratio = current_round / max_rounds drives cosine decay curves.

### Score Extension

- [ ] **P26-SCORE**: BranchScore extended with generalization_gap and
  overfitting_risk fields (backward-compatible defaults). ScoringService
  extended with compute_generalization_signals function.

### Cross-Branch Communication and Merge

- [x] **P27-KERNEL**: Interaction-kernel helpers compute pairwise utility with
  time decay, score-delta weighting, numerically stable softmax normalization,
  and budget-aware branch sampling for cross-branch communication.
- [x] **P27-INJECT**: Branch sharing can inject the global best branch plus
  sampled peer hypotheses into a target branch context, create SHARED DAG
  edges, and record share decisions for topology traceability.
- [x] **P27-COMPONENT**: Phase 27 defines a ComponentClass taxonomy plus
  component-coverage and semantic-complementarity scoring primitives that
  quantify how branches differ and where they can be merged.
- [x] **P27-SELECT**: Merge-stage parent selection uses complementarity-aware
  scoring to prefer multiple parents with non-overlapping strengths when the
  budget enters the convergence stage.
- [x] **P27-PRUNE4**: Dynamic pruning adds a fourth signal that protects
  branches carrying unique component classes absent from the current global
  best branch.
- [x] **P27-MERGE**: Merge orchestration can analyze complementary branches,
  synthesize a unified candidate, create MERGED DAG edges, and gate acceptance
  with a holdout-style validation check.
- [x] **P27-E2E**: Integration coverage proves the full Phase 27 lifecycle:
  sharing, pruning with signal 4, and complementary merge execution in one
  coherent round.

## v2 Requirements

### Future Pipeline UX

- **GUIDE-06**: Pipeline can offer a unified progress and next-step surface
  across multiple runs and branches without forcing manual state inspection.
- **ENV-01**: Pipeline can guide environment repair through machine-readable
  remediation steps or semi-automated fix flows.

## Out of Scope

| Feature | Reason |
|---------|--------|
| New ML model architectures or benchmark improvements | This milestone is about pipeline experience, not task-solving quality |
| Rewriting the core orchestration contracts from scratch | Existing V3 contracts already exist; the gap is user guidance and control-plane quality |
| Adding a new public transport/server abstraction | The standalone surface remains skill/CLI-first |
| Web UI / REST API | Out of scope for this iteration of pipeline hardening |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROUTE-01 | Phase 22 | Complete |
| ROUTE-02 | Phase 22 | Complete |
| PREFLIGHT-01 | Phase 23 | Complete |
| PREFLIGHT-02 | Phase 23 | Complete |
| STATE-01 | Phase 23 | Complete |
| STATE-02 | Phase 23 | Complete |
| GUIDE-05 | Phase 24 | Complete |
| P26-DAG | Phase 26 | Planned |
| P26-SELECT | Phase 26 | Planned |
| P26-PRUNE | Phase 26 | Planned |
| P26-DIVERSITY | Phase 26 | Planned |
| P26-ROUND | Phase 26 | Planned |
| P26-SCORE | Phase 26 | Planned |
| P27-KERNEL | Phase 27 | Complete |
| P27-INJECT | Phase 27 | Complete |
| P27-COMPONENT | Phase 27 | Complete |
| P27-SELECT | Phase 27 | Complete |
| P27-PRUNE4 | Phase 27 | Complete |
| P27-MERGE | Phase 27 | Complete |
| P27-E2E | Phase 27 | Complete |

**Coverage:**
- v1 requirements: 7 total, 7 complete
- v1.3 convergence requirements: 13 total, completion tracked in the traceability table above
- Unmapped: 0

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-23 after Phase 26 planning*
