# Phase 18: Standalone Packaging and Planning Autonomy - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase hardens the standalone repository so a developer can install it,
validate it, expose its repo-local skills to Claude Code and Codex, and
continue standalone GSD planning without relying on the upstream worktree. It
covers packaging/install guidance, agent skill exposure, verification posture,
public-vs-internal documentation boundaries, and cleanup of stale upstream
handoff residue. It does not add new orchestration capabilities, new runtime
semantics, or a new product surface beyond the existing skills-plus-CLI model.

</domain>

<decisions>
## Implementation Decisions

### Skill installation and exposure
- `skills/` remains the canonical source of truth for repo-local skill
  packages.
- Phase 18 should add a repo-local installer/linker workflow that exposes these
  skills into agent-recognized roots instead of expecting agents to scan the
  git repo directly.
- The supported targets are both Codex and Claude Code.
- The supported installation locations are both global and local:
  `~/.codex/skills/`, `~/.claude/skills/`, `./.codex/skills/`, and
  `./.claude/skills/`.
- The default installation mode is symbolic linking, not copying.
- A copy-style fallback may exist only as a compatibility backstop, not as the
  primary workflow.
- Skill installation must not move or duplicate CLI tools.

### CLI runtime contract
- CLI tools remain repo-environment-owned rather than agent-root-owned.
- The standard usage model for `rdagent-v3-tool` is from the cloned repo's
  environment, not as a globally installed shell command contract.
- Phase 18 should preserve the existing `rdagent-v3-tool` console entrypoint
  while documenting repo-environment execution as the canonical operator path.
- Skill installation and CLI execution must be documented as two separate
  flows: skill discovery for agents, tool execution from the repo environment
  for users and agents.

### Verification posture
- Phase 18 should document and implement two verification levels: `Quick` and
  `Full`.
- `Quick` should prove the standalone repo is usable with minimal setup.
- `Full` should prove public-surface integrity, continuity integrity, and
  broader regression health before calling the repo hardened.
- Verification guidance should match the new install/runtime split: skills can
  be linked into agent roots, but CLI validation remains repo-environment
  based.

### Public vs internal documentation boundary
- `README.md` is a public user-facing document and must not retain session
  continuation, planning recovery, or developer-only workflow sections.
- README should describe:
  what the repo ships, how to set up the repo environment, how to expose skills
  to agents, how to run CLI tools, and how to run quick/full validation.
- README should not describe:
  `.planning/` reading order, current milestone recovery, or internal GSD
  operator instructions.
- Internal continuity for standalone planning should move to
  `.planning/STATE.md`, which becomes the canonical internal resume entrypoint.

### Historical cleanup and continuity
- Phase 18 should thoroughly clean stale upstream residue from active docs,
  rather than merely deprioritizing it.
- Active docs must not point to removed `docs/context/*` paths, stale absolute
  machine-local paths, or upstream-worktree continuation steps.
- Historical artifacts may remain as archives, but they must no longer present
  themselves as the current source of truth.
- The standalone repo's `.planning/` tree should be sufficient for future GSD
  work without requiring upstream references.

### Claude's Discretion
- The exact installer command name, script location, and argument syntax may be
  chosen during planning as long as the runtime/location choices above are
  explicit and decision-complete.
- The exact composition of the `Quick` and `Full` verification commands may be
  chosen during planning as long as they preserve the locked two-tier posture.
- Whether compatibility copy mode is exposed as a flag, secondary command, or
  repair path is flexible as long as symlink install remains the default.

</decisions>

<specifics>
## Specific Ideas

- Mirror the install model used by `gsd-build/get-shit-done`: choose target
  runtime plus install location, while keeping repo-owned sources canonical.
- Treat agent skill discovery and CLI runtime as intentionally separate layers:
  agents discover linked `SKILL.md` files from recognized roots, but CLI tools
  keep running from the repo environment.
- Remove the current README "Continue This Session" style content entirely so
  the public narrative stops leaking internal project-maintenance context.
- Make `.planning/STATE.md` the single internal "start here / resume here"
  document for standalone planning continuity.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase truth and active requirements
- `.planning/PROJECT.md` — Milestone goal, standalone positioning, active
  packaging/autonomy requirement, and product-surface constraints.
- `.planning/ROADMAP.md` — Phase 18 boundary, success criteria, and the
  explicit `STANDALONE-01` / `STANDALONE-02` mapping.
- `.planning/REQUIREMENTS.md` — Requirement definitions for self-contained
  install/validation and repo-local planning continuity.
- `.planning/STATE.md` — Current milestone state and the intended next-step
  handoff into Phase 18.

### Current public and package surface
- `README.md` — Current public narrative; contains install and verification
  sections plus an internal continuation section that Phase 18 should remove.
- `pyproject.toml` — Current package metadata and the existing
  `rdagent-v3-tool` console script contract.
- `skills/rd-agent/SKILL.md` — Representative repo-local skill package showing
  the current canonical skill source location.
- `skills/rd-tool-catalog/SKILL.md` — Representative repo-local skill package
  tied to the public tool-catalog surface.

### Current validation and stale handoff seams
- `tests/test_v3_tool_cli.py` — Current CLI contract assertions around
  `rdagent-v3-tool`.
- `tests/test_phase17_surface_convergence.py` — Current README/planning
  terminology regression that will need to adapt once README stops carrying
  internal continuation content.
- `.planning/V3-EXTRACTION-HANDOFF.md` — Historical handoff artifact that still
  contains stale startup instructions and removed `docs/context/*` references
  that Phase 18 should clean or demote.
- `.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-CONTEXT.md`
  — Locked public-surface decisions from the immediately preceding phase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/`: already contains the six public repo-local skill packages that can
  act as installer inputs without redefining the skill surface.
- `pyproject.toml`: already declares the package metadata and the single CLI
  console script `rdagent-v3-tool`.
- `README.md`: already separates install, routing, and verification sections,
  so it can be reworked into a cleaner public-only document rather than rebuilt
  from scratch.
- `.planning/STATE.md`: already acts like a session summary and can become the
  stronger continuity anchor for internal planning.

### Established Patterns
- The public product surface is already locked as `skills + CLI tools`; Phase
  18 must preserve that model rather than inventing a registry/server layer.
- Repo-local skill packages are already the truth source; the missing piece is
  exposure into agent-recognized roots.
- Validation is already documented as command-oriented shell flows, so the new
  quick/full posture can extend the existing style.
- `.planning/` is already the active source of roadmap, requirements, and state
  truth; Phase 18 should harden this rather than creating a parallel planning
  surface elsewhere.

### Integration Points
- Any new skill installer/linker must connect the existing `skills/` tree to
  Claude/Codex skill roots without changing skill package contents.
- README, package metadata, and tests must align on the repo-environment CLI
  contract.
- `.planning/STATE.md` and `.planning/V3-EXTRACTION-HANDOFF.md` are the key
  continuity documents that need responsibility re-assignment: STATE becomes
  current truth, handoff becomes archive/history.
- Public-surface regression tests from Phase 17 will need to be updated to
  reflect the new README boundary without regressing the skills-plus-CLI model.

</code_context>

<deferred>
## Deferred Ideas

- Shipping additional standalone console commands beyond `rdagent-v3-tool`
  belongs to a later phase if the product surface needs more direct CLI entry
  points.
- Automatic skill discovery/runtime support that removes the need for explicit
  install/link steps belongs to a later phase.
- Any broader packaging or distribution strategy beyond self-contained repo use
  and agent skill exposure belongs to a later phase.

</deferred>

---

*Phase: 18-standalone-packaging-and-planning-autonomy*
*Context gathered: 2026-03-21*
