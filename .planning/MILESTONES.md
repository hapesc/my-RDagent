# Project Milestones: my-RDagent-V3

## v1.2 skill-and-tool-guidance-hardening (Shipped: 2026-03-22)

**Delivered:** Made the standalone V3 surface executable from public skill and
tool guidance alone, including direct-tool examples/routing, explicit
stage-skill start and continue contracts, and an agent-first README playbook.

**Phases completed:** 3 phases, 5 plans, 10 tasks

**Key accomplishments:**

- Added concrete examples, routing guidance, and follow-up semantics to every
  direct V3 tool entry.
- Locked `rd-agent` minimum start guidance and the default gated pause behavior
  into the public skill surface.
- Locked paused-run continuation contracts for `rd-propose`, `rd-code`,
  `rd-execute`, and `rd-evaluate`.
- Recast `README.md` into an executable `Start -> Inspect -> Continue`
  playbook.
- Added focused doc-surface regressions so the public README and skill/tool
  guidance cannot drift back into schema-only reference text.

**What's next:** define the next milestone with `$gsd-new-milestone`

---

## v1.1 standalone-surface-consolidation (Shipped: 2026-03-21)

**Delivered:** Hardened the standalone repo around a skills-plus-CLI public surface, repo-local skill installation, and `.planning/`-native continuity.

**Phases completed:** 2 phases, 5 plans, 13 tasks

**Key accomplishments:**

- Renamed the public V3 surface around skills plus CLI tools instead of MCP-era wording.
- Added repo-local installer/linker support for Claude and Codex local/global skill roots.
- Rewrote README around truthful repo setup, CLI usage, and quick/full verification commands.
- Promoted `.planning/STATE.md` to the canonical standalone continuity entrypoint and locked the boundary with doc regressions.

**What's next:** start the next standalone milestone with `$gsd-new-milestone`

---

## v1.0 Standalone V3 Baseline (Shipped: 2026-03-21)

**Delivered:** Imported and stabilized the standalone V3 baseline with self-contained contracts, orchestration, skills, and CLI tool catalog.

**Phases completed:** 12-16 (24 plans total)

**Key accomplishments:**

- Preserved the clean split between V3 product layers and legacy runtime assumptions
- Extracted V3 into a standalone repository
- Replaced the old in-process MCP compatibility layer with a CLI-oriented tool catalog
- Internalized Phase 16 helper algorithms into `v3/algorithms`

**What's next:** v1.1 standalone surface consolidation, including requirement terminology cleanup and planning autonomy

---
