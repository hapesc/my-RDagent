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

## Last Shipped Milestone: v1.3 Pipeline Experience Hardening

**Delivered:** Made the rdagent pipeline behave like an operator assistant
instead of an exposed state machine — added intent routing, early preflight,
truthful state-aware guidance, adaptive DAG exploration with parent selection
and dynamic pruning, cross-branch sharing and complementary merge, holdout
calibration with standardized ranking, and default external dependency ports.

## Current State

- 23,690 lines of Python across the standalone V3 repository.
- 4 shipped milestones (v1.0 → v1.3), 33 requirements satisfied in v1.3.
- The public `rd_agent` entrypoint routes plain-language intent through
  persisted state, prefers paused-run continuation, checks preflight truth,
  and exposes concise operator guidance with next-action recommendations.
- Adaptive DAG path management: SelectParents with 3-dimensional signal model,
  multi-signal dynamic pruning, first-layer diversity via HypothesisSpec.
- Cross-branch communication: interaction-kernel peer sampling, global-best
  injection, component-class taxonomy, and complementary merge with holdout.
- Aggregated validation: K-fold holdout calibration, standardized ranking,
  candidate collection, and finalization operator summary.
- Default external ports (holdout, evaluation, embedding) reduce setup friction.
- Entry wiring degrades gracefully when holdout evaluator is absent.
- `ExplorationMode.FINALIZED` is the single terminal run-state signal.

## Next Milestone

No active milestone. Run `/gsd:new-milestone` to plan the next one.

## Requirements

### Validated

- ✓ Imported standalone V3 baseline from upstream clean-split rebuild — v1.0
- ✓ Skill/CLI-first V3 surface extracted into its own repository — v1.0
- ✓ MCP-era terminology replaced with a consistent skills-plus-CLI public surface — v1.1
- ✓ Standalone repo packaging, install, and validation flow hardened — v1.1
- ✓ Standalone planning continuity now lives fully inside `.planning/` artifacts — v1.1
- ✓ Developers can inspect direct V3 tools and see example requests, routing guidance, and expected follow-up actions — v1.2
- ✓ Developers can use `rd-agent` and the stage skills with explicit minimal input contracts and default stop/continue semantics — v1.2
- ✓ README and tests describe the standalone surface as an executable pipeline rather than a schema catalog — v1.2
- ✓ Intent-first routing routes plain-language user intent to start, continue, inspect, or downshift — v1.3
- ✓ Preflight truth checks runtime, dependency, artifact, state, and recovery readiness — v1.3
- ✓ Operator guidance provides concise state/reason/next-action answers — v1.3
- ✓ Adaptive DAG with SelectParents, dynamic pruning, and first-layer diversity — v1.3
- ✓ Cross-branch sharing, complementary merge, and holdout-gated acceptance — v1.3
- ✓ K-fold holdout calibration, standardized ranking, and finalization guidance — v1.3
- ✓ Default holdout/evaluation/embedding ports and graceful degradation — v1.3

### Active

None — next milestone not yet planned.

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
| Prioritize intent routing and preflight over exposing raw stage mechanics | A user should not need to reason about orchestration internals before the pipeline becomes useful | ✓ Good — v1.3 |
| Implement R&D-Agent convergence as 4 layered phases (DAG→sharing→holdout→ports) | Each layer builds on the previous without circular dependencies | ✓ Good — v1.3 |
| Use abstract ports for holdout and embedding | Keeps core orchestration free from concrete ML framework dependencies | ✓ Good — v1.3 |
| Provide default port implementations with zero external deps | Reduces setup friction without sacrificing the port abstraction | ✓ Good — v1.3 |

---
*Last updated: 2026-03-25 after v1.3 milestone*
