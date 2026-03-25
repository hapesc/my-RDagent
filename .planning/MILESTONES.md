# Project Milestones: my-RDagent-V3

## v1.3 pipeline-experience-hardening (Shipped: 2026-03-25)

**Delivered:** Made the rdagent pipeline behave like an operator assistant
instead of an exposed state machine — added intent routing, early preflight,
truthful state-aware guidance, adaptive DAG exploration with parent selection
and dynamic pruning, cross-branch sharing and complementary merge, holdout
calibration with standardized ranking, and default external dependency ports.

**Phases completed:** 10 phases, 27 plans
**Timeline:** 4 days (2026-03-22 → 2026-03-25)
**Stats:** 204 commits, 295 files changed, +42,410 / -1,873 lines

**Key accomplishments:**

- Intent-first routing: `rd-agent` routes plain-language intent through
  persisted state, prefers paused-run continuation, and exposes next-skill
  guidance without requiring users to choose a skill first.
- Preflight truth hardening: canonical preflight checks runtime, dependency,
  artifact, state, and recovery readiness before stage execution claims.
- Operator guidance UX: shared `OperatorGuidance` contract and renderer
  provide concise current-state / reason / next-action answers.
- Adaptive DAG path management: SelectParents with 3-dimensional signal model,
  multi-signal dynamic pruning with cosine-decay threshold, and first-layer
  diversity via HypothesisSpec category uniqueness.
- Cross-branch communication and merge: interaction-kernel peer sampling,
  global-best injection, component-class taxonomy, and complementary merge
  with holdout gating.
- Aggregated validation: K-fold holdout calibration, standardized ranking,
  candidate collection from frontier+merged nodes, and finalization guidance
  via operator summary.
- Default external ports: DefaultHoldoutSplitPort, DefaultEvaluationPort, and
  DefaultEmbeddingPort (TF-IDF, zero external deps) reduce setup friction.
  Graceful degradation when holdout evaluator is absent.

---

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
