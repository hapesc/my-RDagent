# Requirements: my-RDagent-V3

**Defined:** 2026-03-22
**Core Value:** A developer can use a self-contained V3 skill and CLI surface on
top of V3-owned contracts and orchestration, without reading source code just
to discover how to start, pause, resume, or continue the loop.

## v1 Requirements

### Intent Routing

- [ ] **ROUTE-01**: User can describe work in plain language and the pipeline
  chooses the correct high-level path: start a new run, continue a paused run,
  inspect state, or downshift only when necessary.
- [ ] **ROUTE-02**: When paused work already exists, the pipeline surfaces the
  current run and stage and recommends the next valid skill instead of opening
  a new run by default.

### Preflight and Environment

- [ ] **PREFLIGHT-01**: Before stage execution advances state, the pipeline
  checks required runtime versions and Python dependencies and reports exact
  missing prerequisites with concrete fix guidance.
- [ ] **PREFLIGHT-02**: Before a stage consumes data, artifacts, or state, the
  pipeline checks that required files and snapshots exist and blocks early with
  an explicit reason when they do not.

### State Truth

- [ ] **STATE-01**: User-visible claims such as “next stage ready” are backed
  by persisted stage snapshots and current handoff artifacts rather than surface
  prose alone.
- [ ] **STATE-02**: Verification can distinguish “results exist” from
  “environment is reproducible” and records that difference as a first-class
  blocked or passed state.

### Operator Guidance

- [ ] **GUIDE-05**: User can ask what to do next and receive a concise answer
  that states the current state, the reason for the recommendation, and the
  exact next action without requiring orchestration jargon.

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
| ROUTE-01 | Phase 22 | Pending |
| ROUTE-02 | Phase 22 | Pending |
| PREFLIGHT-01 | Phase 23 | Pending |
| PREFLIGHT-02 | Phase 23 | Pending |
| STATE-01 | Phase 23 | Pending |
| STATE-02 | Phase 23 | Pending |
| GUIDE-05 | Phase 24 | Pending |

**Coverage:**
- v1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 after defining v1.3 milestone requirements*
