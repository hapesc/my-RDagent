# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.2 — Skill and Tool Guidance Hardening

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

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | imported baseline suites | phase-level verification | adapter/internalization work |
| v1.1 | 43-test standalone gate | public surface + continuity regressions | stdlib-only skill installer |
| v1.2 | 68-test public-surface gate | tool metadata + skill contracts + README narrative | no new runtime deps; guidance layered onto existing surfaces |

### Top Lessons (Verified Across Milestones)

1. Keep the standalone public surface narrow and explicit; fake compatibility abstractions create planning debt.
2. Repo-local planning artifacts scale better when milestone history is archived and current-state files stay small.
3. Public guidance becomes materially more usable when README, skill docs, and tool metadata all tell the same operator story.
