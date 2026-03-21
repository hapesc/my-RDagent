# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

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

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | imported baseline suites | phase-level verification | adapter/internalization work |
| v1.1 | 43-test standalone gate | public surface + continuity regressions | stdlib-only skill installer |

### Top Lessons (Verified Across Milestones)

1. Keep the standalone public surface narrow and explicit; fake compatibility abstractions create planning debt.
2. Repo-local planning artifacts scale better when milestone history is archived and current-state files stay small.
