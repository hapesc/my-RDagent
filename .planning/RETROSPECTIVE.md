# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.3 — Pipeline Experience Hardening

**Shipped:** 2026-03-25
**Phases:** 10 | **Plans:** 27 | **Timeline:** 4 days

### What Was Built
- Intent-first routing routes plain-language user intent through persisted state, prefers paused-run continuation, and exposes next-skill guidance.
- Canonical preflight checks runtime, dependency, artifact, state, and recovery readiness before stage execution claims.
- Shared OperatorGuidance contract and renderer provide concise state/reason/next-action answers.
- Adaptive DAG path management with SelectParents (3-dimensional signal model), multi-signal dynamic pruning, and first-layer diversity.
- Cross-branch communication via interaction-kernel peer sampling, global-best injection, component-class taxonomy, and complementary merge.
- K-fold holdout calibration, standardized ranking, candidate collection, and finalization operator summary.
- Default holdout/evaluation/embedding ports with zero external deps and graceful degradation.

### What Worked
- Layered phase decomposition (routing → preflight → guidance → DAG → sharing → holdout → wiring → verification → ports) let each phase build on stable contracts without circular dependencies.
- Adding gap-closure phases (29, 30, 31) after the milestone audit caught integration and traceability issues that would have shipped as silent no-ops.
- TDD with focused regression suites kept each plan verifiable independently.
- Pure math helpers (decay curves, softmax, complementarity scoring) behind typed port boundaries made orchestration services testable without ML framework dependencies.

### What Was Inefficient
- The milestone audit (pre-Phase 29) found 3 critical integration gaps at the rd_agent entry layer that should have been caught during Phase 27/28 execution — service tests passed but the public entrypoint was never wired.
- REQUIREMENTS.md traceability checkboxes fell behind until Phase 30 closed 13 checkboxes in one batch — incremental checkbox updates would have reduced audit noise.
- Some ROADMAP.md phase detail sections became stale (showing wrong plan references) as phases were added dynamically.

### Patterns Established
- Always wire new services into the public entrypoint before marking the phase complete — isolated service tests are insufficient.
- Use abstract ports for external ML dependencies (holdout evaluation, embedding) and provide stdlib defaults.
- Milestone audits before completion catch integration gaps that per-phase verification misses.
- ExplorationMode enum as the single terminal state signal — avoid redundant boolean flags.

### Key Lessons
1. Service-layer tests passing does not mean the public entry path works. Integration wiring must be verified through the real entrypoint.
2. 4-layer convergence architecture (DAG → sharing → holdout → ports) scales when each layer's contracts are frozen before the next layer starts.
3. Default port implementations with zero external deps dramatically reduce setup friction while preserving the abstraction for production use.
4. Gap-closure phases after audit are cheaper than shipping silent no-ops and fixing them post-release.

### Cost Observations
- Model mix: Opus orchestration + Sonnet executors/verifiers
- Sessions: multiple across 4 days
- Notable: The largest milestone so far (10 phases, 27 plans) — convergence mechanism phases (26-28) were the most complex, each requiring 4-6 plans

**Shipped:** 2026-03-22
**Phases:** 3 | **Plans:** 5 | **Sessions:** 1

### What Was Built
- Direct V3 tools now expose concrete request examples, explicit routing boundaries, and follow-up semantics from the public tool catalog itself.
- `rd-agent` and the four stage skills now expose explicit start and paused-run continuation contracts through their public `SKILL.md` surfaces.
- `README.md` now acts as an agent-first `Start -> Inspect -> Continue` playbook instead of a disconnected schema-oriented reference.

### What Worked
- Splitting the milestone into tool metadata, skill contracts, and README narrative kept each phase narrow and evaluable.
- File-reading regressions over tool payloads, skill docs, and README caught public-surface drift quickly without requiring snapshots.
- Treating missing-field recovery as an agent responsibility produced a more coherent public story than sending users to browse tools manually.

### What Was Inefficient
- Parallel executor commits kept colliding on the shared git index, repeatedly leaving transient `.git/index.lock` failures that had to be retried.
- Completion tooling handled the mechanical archive, but milestone-quality summaries, archive cleanup, and PROJECT evolution still needed manual repair afterward.
- Some legacy tests and config expectations, such as the `.importlinter` mismatch against a Phase 14 test, remained out-of-scope noise during later phase verification.

### Patterns Established
- Put operator guidance on the real public surfaces: tool metadata, skill packages, and README, instead of inventing a second docs-only catalog.
- Keep README at the decision layer and link to the real contracts for field-level truth.
- Model the public flow as `Start -> Inspect -> Continue`, with `rd-agent` first and `rd-tool-catalog` only as a downshift path.

### Key Lessons
1. Product-surface hardening works best when the same guidance is locked at three layers together: tool payloads, skill contracts, and README narrative.
2. Parallel phase execution needs better git isolation; otherwise orchestration wins speed but loses reliability at commit boundaries.
3. Milestone archival should not trust raw automation output blindly, because the human-facing archive quality matters as much as the raw file movement.

### Cost Observations
- Model mix: orchestrator plus targeted executor/verifier/researcher agents
- Sessions: 1
- Notable: focused public-surface regressions scaled well, but archival and git-tagging still required manual correction around generated artifacts and transient git locks

---

## Milestone: v1.1 — Standalone Surface Consolidation

**Shipped:** 2026-03-21
**Phases:** 2 | **Plans:** 5 | **Sessions:** 1

### What Was Built
- Skill and CLI terminology was converged across README, requirements, roadmap, tests, and skill packages.
- Repo-local skill installation now links canonical `skills/` packages into Claude/Codex local and global roots.
- Standalone planning continuity now lives in `.planning/STATE.md` with doc regressions guarding the public/internal split.

### What Worked
- Breaking the milestone into terminology first and packaging/continuity second kept each phase outcome crisp.
- Direct file-reading regressions caught doc-surface drift quickly and cheaply.

### What Was Inefficient
- Multiple subagents finished most of the implementation work but hung during completion handoff, forcing orchestrator spot-check fallback.
- Milestone archival tooling captured only raw archives; human-facing milestone summary and roadmap compression still required manual cleanup.

### Patterns Established
- Use repo-local installer wrappers for agent setup while keeping the public CLI surface flat.
- Treat README as public-only and `.planning/STATE.md` as the canonical internal continuity contract.
- Prefer summary/verification spot-check fallback when agent completion signaling is unreliable but commits and artifacts exist.

### Key Lessons
1. Completion workflows need artifact-based verification fallbacks because agent handoff can fail after successful tool execution.
2. Public/internal documentation boundaries are stable when enforced with direct string regressions instead of narrative conventions.

### Cost Observations
- Model mix: primarily local orchestrator work plus GSD executor/verifier spot usage
- Sessions: 1
- Notable: small, focused regression suites made repeated verification cheap while the orchestrator recovered from subagent completion failures

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 1 | 5 | Imported upstream baseline into standalone repo |
| v1.1 | 1 | 2 | Added standalone-native packaging, continuity, and doc-boundary hardening |
| v1.2 | 1 | 3 | Unified tool metadata, skill contracts, and README into one executable public guidance surface |
| v1.3 | multi | 10 | Intent routing, preflight, operator guidance, 4-layer convergence mechanism, default ports |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | imported baseline suites | phase-level verification | adapter/internalization work |
| v1.1 | 43-test standalone gate | public surface + continuity regressions | stdlib-only skill installer |
| v1.2 | 68-test public-surface gate | tool metadata + skill contracts + README narrative | no new runtime deps; guidance layered onto existing surfaces |
| v1.3 | 100+ regression tests | intent routing + preflight + DAG + holdout + entry wiring | stdlib TF-IDF embeddings, seeded K-fold splits |

### Top Lessons (Verified Across Milestones)

1. Keep the standalone public surface narrow and explicit; fake compatibility abstractions create planning debt.
2. Repo-local planning artifacts scale better when milestone history is archived and current-state files stay small.
3. Public guidance becomes materially more usable when README, skill docs, and tool metadata all tell the same operator story.
4. Service-layer tests passing does not mean the public entry path works — always verify through the real entrypoint.
5. Abstract ports with stdlib defaults reduce setup friction without sacrificing the abstraction boundary.
