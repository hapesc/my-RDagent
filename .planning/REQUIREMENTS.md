# Requirements: V3 Clean-Split Rebuild

**Defined:** 2026-03-19
**Core Value:** A truly agent-first V3 architecture that is cleanly separated from the existing V2 runtime rather than layered on top of it.

## Boundary Separation

- [x] **V3-BOUNDARY-01**: Developer can identify a V3-owned entry layer that is distinct from V2 CLI/runtime entrypoints.
- [x] **V3-BOUNDARY-02**: Developer can identify a V3-owned orchestration layer that does not rely on V2 graph internals as the product-facing control plane.
- [x] **V3-BOUNDARY-03**: Developer can identify a V3-owned public state contract whose truth does not depend on exposing raw V2 internal payloads.
- [x] **V3-BOUNDARY-04**: Developer can identify an explicit compatibility layer for any retained V2 workflows instead of letting compatibility semantics leak into core V3 design.

## V3 Runtime and State Contracts

- [x] **V3-RUNTIME-01**: Developer can start a V3 run through V3-owned agent-facing contracts and tools rather than a V2 runtime path.
- [x] **V3-RUNTIME-02**: Developer can observe V3 lifecycle transitions in V3 terms, without needing V2 graph/node vocabulary.
- [x] **V3-STATE-01**: Developer can treat V3 public state artifacts as the authoritative external truth.
- [x] **V3-STATE-02**: Developer can distinguish public V3 recovery semantics from private execution-engine checkpoint mechanics.
- [x] **V3-TOOLS-01**: Developer can use rebuilt V3-owned exploration/execution tools for capabilities still needed from V2, rather than routing through V2 compatibility surfaces.
- [x] **V3-TOOLS-02**: Developer can identify which algorithmic tools were intentionally rebuilt for V3 and consume them without importing V2 runtime modules.

## Skills and Orchestration

- [x] **SKILL-01**: Developer can start a full autonomous R&D loop with `/rd-agent` as the primary V3 entrypoint.
- [x] **SKILL-02**: Developer can invoke `/rd-propose`, `/rd-code`, `/rd-execute`, and `/rd-evaluate` independently without direct dependence on V2 runtime internals.
- [x] **SKILL-03**: Developer can resume an interrupted run from persisted artifacts without recomputing completed stages.
- [x] **SKILL-04**: Developer can configure hard iteration ceilings and unattended vs gated execution for `/rd-agent`.

## Memory and Branch State

- [x] **MEM-01**: Developer can persist hypothesis, score, reason, outcome, and branch metadata through V3-facing contracts.
- [x] **MEM-02**: Developer can retrieve ranked context notes through V3-facing contracts using the intended ranking policy.
- [x] **MEM-03**: Developer can share high-quality discoveries across branches without overwhelming local branch context.
- [x] **ARTF-03**: Developer can isolate branch state through branch-scoped artifact/workspace directories that are part of the V3 contract.

## Exploration and Tool Surface

- [x] **MCP-02**: Developer can call the complete structured `rd_*` tool surface from Claude Code for exploration, memory, and scenario stages.
- [x] **EXPL-01**: Developer can delegate multiple exploration branches to subagents in parallel, with one isolated artifact workspace per branch.
- [x] **EXPL-02**: Developer can select the next branch with PUCT through V3-exposed tools instead of implicit model preference.
- [x] **EXPL-03**: Developer can expand promising branches and prune weak branches while recording those decisions in run artifacts.
- [x] **EXPL-04**: Developer can synchronize branch outcomes back into shared V3 run state coherently.
- [x] **EXPL-05**: Developer can synthesize top-K branch results and automatically fall back to the top-1 branch when merge quality degrades.

## Rejected Legacy Parity Goals

These are explicitly out of scope for the clean-split rebuild:

- **COMPAT-01**: Preserving `python -m v2 run` as a V3 compatibility path.
- **COMPAT-02**: Matching historical V2 pause/resume semantics.
- **TEST-01**: Matching a golden V2 execution trace as a V3 success condition.
- **SDK-01**: Treating future SDK swaps as a reason to preserve V2-shaped contracts.

## Traceability

| Requirement | Planned Phase | Status |
|-------------|---------------|--------|
| V3-BOUNDARY-01 | Phase 12 | Completed in 12-01 |
| V3-BOUNDARY-02 | Phase 12 | Completed in 12-01 |
| V3-BOUNDARY-03 | Phase 12 | Completed in 12-02 |
| V3-BOUNDARY-04 | Phase 12 | Completed in 12-02 |
| V3-RUNTIME-01 | Phase 13 | Complete |
| V3-RUNTIME-02 | Phase 13 | Complete |
| V3-STATE-01 | Phase 13 | Complete |
| V3-STATE-02 | Phase 13 | Complete |
| V3-TOOLS-01 | Phase 13 | Complete |
| V3-TOOLS-02 | Phase 13 | Complete |
| SKILL-01 | Phase 14 | Complete |
| SKILL-02 | Phase 14 | Complete |
| SKILL-03 | Phase 14 | Complete |
| SKILL-04 | Phase 14 | Complete |
| MEM-01 | Phase 15 | Complete |
| MEM-02 | Phase 15 | Complete |
| MEM-03 | Phase 15 | Complete |
| ARTF-03 | Phase 15 | Complete |
| MCP-02 | Phase 16 | Complete |
| EXPL-01 | Phase 16 | Complete |
| EXPL-02 | Phase 16 | Complete |
| EXPL-03 | Phase 16 | Complete |
| EXPL-04 | Phase 16 | Complete |
| EXPL-05 | Phase 16 | Complete |
