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

## Last Shipped Milestone: v1.1 Standalone Surface Consolidation

**Delivered:** Turned the extracted V3 baseline into a standalone skill/CLI-first
product surface with repo-local installation, truthful public docs, and
`.planning/`-native continuity.

## Current Milestone: v1.2 Skill and Tool Guidance Hardening

**Goal:** Make the standalone V3 surface executable by agents without requiring
source-code spelunking to discover the next valid action.

**Target features:**
- Add tool-layer usage guidance and concrete examples to the V3 CLI catalog.
- Upgrade `rd-agent` and stage skill packages with minimal input contracts,
  stop-point semantics, and continuation guidance.
- Lock the improved guidance in README and regression tests so the public
  surface stays pipeline-usable.

## Next Milestone Goals

- Ship example-driven guidance so agents can invoke the standalone V3 surface
  correctly from skill and tool metadata alone.
- Preserve the repo-local skill/CLI public surface while making it materially
  more actionable for multi-step orchestration work.

## Requirements

### Validated

- ✓ Imported standalone V3 baseline from upstream clean-split rebuild — v1.0
- ✓ Skill/CLI-first V3 surface extracted into its own repository — v1.0
- ✓ MCP-era terminology replaced with a consistent skills-plus-CLI public surface — validated in Phase 17
- ✓ Standalone repo packaging, install, and validation flow hardened — validated in Phase 18
- ✓ Standalone planning continuity now lives fully inside `.planning/` artifacts — validated in Phase 18

### Active

- [ ] Developer can inspect a direct V3 tool and see example requests,
  routing guidance, and expected follow-up actions without reading source.
- [ ] Developer can use `rd-agent` and the stage skills with explicit minimal
  input contracts and default stop/continue semantics.
- [ ] README and tests describe the standalone surface as an executable
  pipeline, not just a schema catalog.

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
- The remaining work is mostly language, packaging, and product-surface
  convergence rather than rebuilding core orchestration from scratch.
- Recent `rd-agent` usage showed a concrete product gap: schema-only tool
  descriptions are structurally valid but do not teach an agent when to use a
  tool, what minimal payload to provide, or what to do after a gated pause.

## Current State

Phase 18 completed the standalone packaging and continuity hardening work:

- repo-local skill installation now links canonical `skills/` packages into
  Claude/Codex local or global roots
- README documents the public setup, CLI usage, and quick/full verification
  flows without leaking internal planning workflow
- `.planning/STATE.md` is the canonical continuity entrypoint, and the
  extraction handoff is historical-only

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
| Treat agent-usable guidance as product work | A schema-only catalog is insufficient when the real surface is a multi-step orchestration pipeline | — Pending — v1.2 |

---
*Last updated: 2026-03-22 after starting v1.2 milestone*
