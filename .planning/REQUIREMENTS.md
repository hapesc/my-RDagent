# Requirements: my-RDagent-V3

**Defined:** 2026-03-22
**Core Value:** A developer can use a self-contained V3 skill and CLI surface on
top of V3-owned contracts and orchestration, without reading source code just
to discover how to start, pause, resume, or continue the loop.

## v1 Requirements

### Tool Guidance

- [ ] **GUIDE-01**: Developer can inspect a direct V3 CLI tool and see one or
  more concrete request examples with realistic arguments for the common path.
- [ ] **GUIDE-02**: Developer can inspect a direct V3 CLI tool and see when to
  use it, when not to use it, and which higher-level skill is preferred when
  the direct tool is the wrong layer.
- [ ] **GUIDE-03**: Developer can inspect a direct V3 CLI tool and understand
  the expected follow-up action after a successful call, especially for
  orchestration and gated-stop results.

### Skill Contracts

- [ ] **SKILL-01**: Developer can start `rd-agent` from the skill package with
  an explicit minimal-input contract that names the required run fields and the
  required stage payload fields.
- [ ] **SKILL-02**: Developer can understand the default `rd-agent` gated
  behavior, including that `gated + max_stage_iterations=1` pauses after the
  first completed stage for operator review.
- [ ] **SKILL-03**: Developer can continue from a paused `rd-agent` run by
  following stage-skill guidance that states the exact identifiers and payload
  fields needed for `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate`.

### Public Surface Narrative

- [ ] **SURFACE-01**: Developer can read README and understand the standalone
  V3 surface as a multi-step skill-and-tool pipeline with concrete start,
  inspect, and continue paths.
- [ ] **SURFACE-02**: Regression tests lock the new guidance fields and examples
  so the tool catalog and skill packages cannot drift back to schema-only
  descriptions.

## v2 Requirements

### Future Guidance Expansion

- **GUIDE-04**: Developer can inspect branch-memory and exploration tools with
  domain-specific example sequences covering multi-branch collaboration.
- **SURFACE-03**: Developer can generate machine-readable operator playbooks for
  common end-to-end standalone V3 flows from the public tool surface itself.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-solving arbitrary competition tasks from prose alone | Product gap is guidance and routing, not replacing stage outputs with hidden reasoning |
| Reintroducing MCP transport/server abstractions | Standalone surface remains skill/CLI-first |
| Rebuilding core orchestration contracts | Existing V3 contracts and orchestration already exist; this milestone hardens operator usability |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GUIDE-01 | Phase 19 | Pending |
| GUIDE-02 | Phase 19 | Pending |
| GUIDE-03 | Phase 19 | Pending |
| SKILL-01 | Phase 20 | Pending |
| SKILL-02 | Phase 20 | Pending |
| SKILL-03 | Phase 20 | Pending |
| SURFACE-01 | Phase 21 | Pending |
| SURFACE-02 | Phase 21 | Pending |

**Coverage:**
- v1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 after roadmap creation for v1.2*
