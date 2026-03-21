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

## Current Milestone: v1.1 Standalone Surface Consolidation

**Goal:** Turn the extracted V3 baseline into a standalone skill/CLI-first
product surface with terminology, packaging, and planning artifacts that no
longer assume an MCP or legacy-shell framing.

**Target features:**
- A CLI-described V3 tool catalog instead of an MCP-shaped registry framing
- Consistent skill/CLI terminology across requirements, roadmap, docs, and tests
- Standalone packaging, install, and verification flow for the extracted V3 repo
- Preserved V3 single-branch and multi-branch orchestration semantics inside the standalone repository

## Requirements

### Validated

- ✓ Imported standalone V3 baseline from upstream clean-split rebuild — v1.0
- ✓ Skill/CLI-first V3 surface extracted into its own repository — v1.0
- ✓ MCP-era terminology replaced with a consistent skills-plus-CLI public surface — validated in Phase 17
- ✓ Standalone repo packaging, install, and validation flow hardened — validated in Phase 18
- ✓ Standalone planning continuity now lives fully inside `.planning/` artifacts — validated in Phase 18

### Active

None. Milestone `v1.1` is complete.

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
| Treat terminology cleanup as real milestone work | Requirement names shape product direction and future planning quality | — Active |

---
*Last updated: 2026-03-21 after Phase 18 verification and v1.1 completion*
