# my-RDagent-V3

## What This Is

A standalone V3 repository extracted from `my-RDagent`, focused on the
agent-first core rather than the legacy app/runtime shell. It contains the V3
contracts, orchestration, skill entrypoints, and CLI-oriented tool surface for
the `propose -> code -> execute -> evaluate -> repeat` loop.

## Core Value

A developer can use a self-contained V3 skill and CLI surface on top of
V3-owned contracts and orchestration, without inheriting V2 runtime internals
or MCP-shaped compatibility layers.

## Last Shipped Milestone: v1.2 Skill and Tool Guidance Hardening

**Delivered:** Made the standalone V3 surface executable from public skill and
tool guidance alone: direct tools now explain request shape, routing, and
follow-up; stage skills now expose explicit start and continuation contracts;
and the README now acts as an agent-first `Start -> Inspect -> Continue`
playbook.

## Current State

- Phase 22 is complete: `rd-agent` now routes plain-language intent through
  persisted state, prefers paused-run continuation, and exposes explicit
  next-skill guidance.
- Phase 23 is complete: canonical preflight truth now checks runtime,
  dependency, artifact, state, and recovery readiness before stage execution
  claims or paused-run continuation guidance say work is executable.
- Paused-run routing now keeps `recommended_next_skill` visible while surfacing
  blocked-vs-executable truth and one concrete repair action.
- Stage entrypoints now return `preflight_blocked` before publishing replay,
  completion, or blocker state when canonical preflight fails.
- The direct V3 tool catalog now exposes concrete examples, routing guidance,
  and next-step semantics through the public `rdagent-v3-tool describe ...`
  surface.
- `rd-agent` and the four stage skills now publish explicit minimum-input and
  paused-run continuation contracts through their `SKILL.md` files.
- `README.md` now explains the public surface as one executable
  `Start -> Inspect -> Continue` path instead of a disconnected schema catalog.
- Public-surface regressions now span README narrative, tool metadata, and
  skill contracts, keeping the operator guidance aligned across all layers.
- Phase 24 is complete: top-level routing, stage outcomes, direct-tool follow-up
  semantics, and public docs now share one human-first next-step vocabulary with
  selective detail expansion.
- Phase 24 introduced a shared `OperatorGuidance` contract and renderer so route
  and stage surfaces can reuse one canonical current-state / reason / next-action
  model instead of hand-assembling strings independently.
- The direct V3 tool catalog now uses the same stage-skill follow-up vocabulary
  as the high-level skill surfaces, so public skill and tool guidance no longer
  drift on "what next?" semantics.
- Phase 29 is complete: the public `rd_agent` entrypoint now wires
  `HoldoutValidationService`, `BranchShareService`, and finalization operator
  guidance into the production multi-branch path, so Phase 27/28 convergence
  work is reachable from the real entry layer instead of isolated service tests.

## Current Milestone: v1.3 Pipeline Experience Hardening

**Goal:** Make the rdagent pipeline feel like an operator assistant instead of
an exposed state machine by improving intent routing, preflight checks, and
next-step guidance.

**Target features:**
- Add intent-first entry and state-aware routing so the system chooses the
  correct skill or resume path before the user has to think in stage names.
- Add early preflight checks for runtime, dependency, data, and state
  contracts so environment blockers are surfaced before stage execution.
- Add a truthful operator UX layer for current state, blocker reason, and next
  action, grounded in real persisted state rather than surface prose alone.
- Use `gsd-build/get-shit-done` as a reference for how a strong pipeline guides
  users through one visible path while hiding orchestration complexity.

## Next Milestone Goals

- Make the default rdagent entrypoint choose the right next action from user
  intent and current persisted state.
- Reduce user-visible orchestration jargon by translating state-machine truth
  into concise operator guidance and explicit recovery steps.
- Harden the pipeline against late environment surprises and surface/state
  mismatches before stage execution begins.

## Requirements

### Validated

- ✓ Imported standalone V3 baseline from upstream clean-split rebuild — v1.0
- ✓ Skill/CLI-first V3 surface extracted into its own repository — v1.0
- ✓ MCP-era terminology replaced with a consistent skills-plus-CLI public surface — validated in Phase 17
- ✓ Standalone repo packaging, install, and validation flow hardened — validated in Phase 18
- ✓ Standalone planning continuity now lives fully inside `.planning/` artifacts — validated in Phase 18
- ✓ Developers can inspect direct V3 tools and see example requests, routing guidance, and expected follow-up actions — validated in Phase 19 / v1.2
- ✓ Developers can use `rd-agent` and the stage skills with explicit minimal input contracts and default stop/continue semantics — validated in Phase 20 / v1.2
- ✓ README and tests describe the standalone surface as an executable pipeline rather than a schema catalog — validated in Phase 21 / v1.2
- ✓ User can start or continue work from high-level intent without having to manually choose `rd-agent`, a stage skill, or a direct tool first — validated in Phase 22 / v1.3
- ✓ Pipeline surfaces runtime, dependency, data, and state blockers before a stage claims to be executable — validated in Phase 23 / v1.3
- ✓ User-facing progress and next-step guidance now stay aligned with persisted state and preflight truth for paused-run and stage-entry surfaces — validated in Phase 23 / v1.3
- ✓ User can ask what to do next and receive a concise answer that states the current state, the reason, and the exact next action without orchestration jargon — validated in Phase 24 / v1.3

### Active

None — v1.3 active requirements are complete.

### Out of Scope

- `python -m v2 run` parity as a design driver
- Exposing V2 graph/checkpoint/runtime vocabulary through V3 user-facing skills or tools
- Reintroducing an MCP transport/server abstraction as the primary V3 surface
- Web UI / REST API
- Multi-GPU / distributed execution

## Context

- This repository starts from an imported V3 baseline that already passed the
  upstream clean-split rebuild.
- The extraction session removed the last in-process `mcp_tools` compatibility
  layer and replaced it with a transport-free CLI tool catalog.
- The standalone repo should now be treated as the primary home for V3 surface
  evolution, not as a mirror of the legacy upstream shell.
- The remaining work is now less about basic public-surface truth and more
  about extending that public guidance into more complex operator scenarios
  without reintroducing hidden orchestration assumptions.
- The shipped `v1.2` milestone closed the original schema-only guidance gap by
  aligning direct-tool metadata, stage-skill contracts, and README narrative.
- Real Kaggle-style test conversations exposed the next layer of product debt:
  users still have to understand too much about orchestration state, environment
  readiness, and skill routing before the pipeline feels helpful.
- The `gsd-build/get-shit-done` pipeline is a useful reference because it keeps
  one visible operator path, a strong “what’s next” model, and explicit
  progress/phase surfaces above its internal orchestration machinery.

## Constraints

- **Tech stack**: Python 3.11+, `pydantic`, `pytest`, and `import-linter`
- **Architecture**: V3 public entrypoints, orchestration, and tool contracts
  must stay self-contained and free from legacy runtime ownership
- **Product surface**: Skills and CLI tools are the primary surface
- **Operator usability**: Agents should be able to advance the V3 loop from
  public docs, skill packages, and tool metadata without reading entrypoint
  source code
- **State truth**: Public run, branch, stage, artifact, recovery, memory, and
  exploration semantics remain V3-owned contracts
- **Testing**: Preserve strong validation discipline and boundary gates inside
  the standalone repository

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Extract V3 into its own repository | Lets V3 evolve without dragging legacy app/runtime shell assumptions forward | ✓ Good — v1.0 |
| Replace MCP-shaped framing with skill/CLI framing | Matches the actual implementation surface and avoids fake transport abstractions | ✓ Good — v1.0 |
| Keep `v3.compat.v2` explicit but non-central | Preserves migration context without making compatibility the product body | ✓ Good — v1.0 |
| Treat terminology cleanup as real milestone work | Requirement names shape product direction and future planning quality | ✓ Good — v1.1 |
| Keep skill installation repo-local and link-first | Preserves one source of truth without widening the public CLI surface | ✓ Good — v1.1 |
| Make `.planning/STATE.md` the continuity truth | Keeps public README separate from internal milestone recovery | ✓ Good — v1.1 |
| Treat agent-usable guidance as product work | A schema-only catalog is insufficient when the real surface is a multi-step orchestration pipeline | ✓ Good — v1.2 |
| Keep README at the decision layer and link to contracts for field-level truth | Prevents the public narrative from drifting into a second schema catalog | ✓ Good — v1.2 |
| Prioritize intent routing and preflight over exposing raw stage mechanics | A user should not need to reason about orchestration internals before the pipeline becomes useful | Intent routing validated in Phase 22; preflight and state-truth hardening validated in Phase 23 |

---
*Last updated: 2026-03-24 after completing Phase 29*
