---
phase: 18-standalone-packaging-and-planning-autonomy
plan: 01
subsystem: infra
tags: [skills, codex, claude, installer, symlink, pytest]
requires:
  - phase: 17-skill-and-cli-surface-terminology-convergence
    provides: repo-local skill packages and the skills-plus-CLI public surface
provides:
  - Repo-local installer logic for Claude and Codex skill roots
  - A thin wrapper script for explicit runtime, scope, and mode selection
  - Regression tests for link, copy, rerun, and broken-link repair flows
affects: [18-02-PLAN.md, README.md, public-docs, onboarding]
tech-stack:
  added: []
  patterns: [repo-local skill linking, stdlib-only installer helpers, filesystem regression tests]
key-files:
  created: [v3/devtools/__init__.py, v3/devtools/skill_install.py, scripts/install_agent_skills.py, tests/test_phase18_skill_installation.py]
  modified: []
key-decisions:
  - "Keep `skills/` as the single source of truth and expose it through local/global Claude/Codex skill roots instead of adding another public packaging surface."
  - "Use symlinks as the default install mode and a managed-marker copy fallback so reruns can repair managed targets without touching unrelated directories."
patterns-established:
  - "Repo-local helper modules may support setup flows as long as the public CLI surface remains `rdagent-v3-tool`."
  - "Skill-install regression coverage uses tmp-path fixture repos so real home-directory roots stay untouched."
requirements-completed: [STANDALONE-01]
duration: 4min
completed: 2026-03-21
---

# Phase 18 Plan 01: Repo-local skill installer summary

**Phase 18 now ships a repo-local Claude/Codex skill installer that links canonical `skills/` packages into local or global agent roots and locks the behavior with deterministic pytest coverage**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-21T22:13:04+08:00
- **Completed:** 2026-03-21T22:17:10+08:00
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added `v3.devtools.skill_install` as a stdlib-only helper layer that discovers repo-local skills, resolves Claude/Codex local/global targets, and installs by link or copy mode.
- Added `scripts/install_agent_skills.py` as a thin repo-local wrapper with explicit `--runtime`, `--scope`, and `--mode` flags.
- Added targeted pytest coverage for symlink installs, idempotent reruns, broken-link repair, copy fallback, and preservation of unrelated targets.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add importable skill install/link logic for Claude and Codex targets** - `53f24e6` (feat)
2. **Task 2: Add the repo-local installer wrapper with explicit runtime and scope flags** - `6a91a63` (feat)
3. **Task 3: Lock installer behavior with targeted pytest coverage** - `2f68543` (test)

## Files Created/Modified

- `v3/devtools/__init__.py` - exports installer helpers for direct import and test access
- `v3/devtools/skill_install.py` - source-of-truth install logic for repo-local skill discovery and managed target repair
- `scripts/install_agent_skills.py` - repo-local wrapper command for local/global Claude/Codex installation
- `tests/test_phase18_skill_installation.py` - filesystem-local regression coverage for installer behavior

## Decisions Made

- Kept the helper layer stdlib-only so Phase 18 does not widen packaging dependencies for a setup-only workflow.
- Treated symlink targets and copy targets with a managed marker as safe-to-repair, while preserving unrelated directories under skill roots.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `18-02` can now document concrete skill installation commands against a real repo-local wrapper instead of speculative setup text.
- Phase 18 verification can rely on the new pytest suite to prove local/global skill exposure behavior without touching the user's real home-directory skill roots.

## Self-Check

PASSED.

---
*Phase: 18-standalone-packaging-and-planning-autonomy*
*Completed: 2026-03-21*
