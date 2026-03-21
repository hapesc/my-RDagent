# R&D-Agent Platform

## What This Is

An autonomous R&D platform implementing the RDAgent paper (arXiv:2505.14738v2): an LLM-driven `propose → code → execute → evaluate → repeat` loop for research and engineering work. This worktree is the `v3.1` clean-split rebuild, which treats the historical V2 runtime as a legacy execution kernel and compatibility reference while rebuilding V3 as an agent-first system with its own entrypoints, orchestration, public state contracts, and skills surface.

## Core Value

A developer can invoke real V3 entrypoints such as `/rd-agent` on top of V3-owned contracts, orchestration, and tools — without the product surface secretly depending on V2 runtime internals.

## Current Milestone: v3.1 Clean-Split Rebuild

**Goal:** Rebuild V3 as a true agent-first architecture with a clean boundary from V2. V3 owns user-facing entrypoints, orchestration, state truth, and skills; V2 remains historical runtime/reference material and an explicit compatibility seam rather than the hidden product body.

**Target features:**
- Real V3 agent-facing contracts and `rd_*` tool surface
- Skills-first UX with `/rd-agent` as primary entrypoint and stage-specific skills for propose/code/execute/evaluate
- V3-owned orchestration, stage reuse, resume, and recovery semantics
- V3-owned memory and branch-isolated state contracts
- Multi-branch orchestration restored only after the single-branch V3 loop is cleanly rebuilt

## Requirements

### Validated

- ✓ 10 technical documents rewritten for v2 architecture — v1.0
- ✓ README + QUICKSTART as verified entry points — v1.0
- ✓ MkDocs site with CI gate — v1.0
- ✓ Paper FC mapping with honest gap analysis — v1.0
- ✓ 18 review fixes (8 Critical + 10 Important) — post-v1.0
- ✓ v1 modules archived to `legacy/` — post-v1.0
- ✓ FC-2 DAG exploration: PUCT selection, Layer-0 diversity, pruning, branch dispatch, trace merging — v2.0
- ✓ FC-4 Memory: SQLite persistence, interaction kernel, proposer injection, cross-branch sharing — v2.0
- ✓ 94% test coverage with full-chain integration tests — v2.0
- ✓ Phase 12 boundary separation and compatibility seam enforcement — v3.1
- ✓ Phase 13 V3 agent-facing contract and minimal tool rebuild — v3.1

### Active

- [ ] Deliver `/rd-agent` as the primary V3 single-branch entrypoint
- [ ] Deliver independent `/rd-propose`, `/rd-code`, `/rd-execute`, and `/rd-evaluate` skills without V2 leakage
- [ ] Make stage skipping, reuse, and resume behavior transparent and V3-owned
- [ ] Keep the public `rd_*` tool surface aligned with V3 contracts rather than V2 implementation details
- [ ] Rebuild V3 memory and branch-isolated state after the single-branch skill loop is stable
- [ ] Restore multi-branch exploration and merge only inside the clean V3 architecture

### Out of Scope

- `python -m v2 run` parity as a design driver — this worktree explicitly rejects V2 compatibility as the core V3 architecture
- Exposing V2 graph/checkpoint/runtime vocabulary through V3 user-facing skills or tools — violates the clean-split boundary
- Multi-branch orchestration before the single-branch V3 loop is cleanly established — sequencing risk
- Web UI / REST API — separate concern, deferred
- Multi-GPU / distributed execution — infrastructure concern
- Marketing website — not in this repo

## Context

- The base repository already contains strong V2 algorithms and coverage; the rebuild should preserve the useful algorithms while removing hidden orchestration coupling
- This worktree exists specifically to reset V3 as a clean architectural split rather than continuing the earlier “MCP + V2 runtime = V3” assumption
- Phase 12 established the boundary anchors and reserved `v3.compat.v2` as the only allowed compatibility seam
- Phase 13 rebuilt the minimal V3 public state, recovery semantics, selection logic, and schema-described tool registry
- Phase 14 is next: skills-first single-branch orchestration on top of the rebuilt V3 contracts and tool surface
- Industry trend (2025-2026): strong coding agents increasingly rely on simple agentic loops with tools and skills rather than graph-first orchestration frameworks

## Constraints

- **Tech stack**: Python 3.11+, existing repo toolchain, and repo-local validation commands must remain usable in this worktree
- **Architecture**: V3 public entrypoints, orchestration, and tool contracts must not secretly depend on V2 runtime internals — this is the whole point of the reset
- **Compatibility**: V2 compatibility may exist only through explicit seams such as `v3.compat.v2`, not as the body of V3
- **Product surface**: Skills are the user-facing product surface, not decorative aliases over old flows
- **State truth**: Public run, branch, stage, artifact, recovery, and later memory semantics must be V3-owned contracts
- **Testing**: Preserve strong validation discipline and prove new V3 behavior with tests and boundary gates

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat prior V3 work as preparatory, not architectural completion | Earlier MCP/data-science bridge work did not prove clean separation from V2 | ✓ Good — v3.1 |
| Make V3 a clean-split rebuild | Prevents “new shell, same hidden runtime” from masquerading as architecture progress | ✓ Good — v3.1 |
| Reserve `v3.compat.v2` as the only compatibility seam | Keeps legacy access explicit and auditable | ✓ Good — v3.1 |
| Rebuild public state and minimal `rd_*` tools before skills | Skills need a truthful V3-owned contract/tool base instead of placeholders | ✓ Good — v3.1 |
| Deliver single-branch skill orchestration before multi-branch features | Reduces complexity and makes stage semantics understandable first | — Pending |
| Keep V2 compatibility out of milestone-driving scope | Prevents architecture drift back toward hidden V2 orchestration | ✓ Good — v3.1 |

---
*Last updated: 2026-03-20 after worktree migration recovery*