# Phase 19: Tool Catalog Operator Guidance - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase hardens the direct V3 CLI tool surface so a developer or agent can
inspect a tool entry and understand three things without reading source code:
the common-path request shape, the correct routing layer, and the next action
after a successful result. The phase is limited to tool-catalog guidance for
existing direct tools. It does not add new orchestration capabilities, rewrite
stage-skill contracts, or broaden the README narrative beyond what is needed to
keep tool metadata truthful.

</domain>

<decisions>
## Implementation Decisions

### Guidance lives in structured tool metadata
- The new operator guidance must live in the structured data emitted by the V3
  tool catalog, not only in prose-only docs or skill references.
- `inputSchema` and `outputSchema` remain the structural contract; the new
  guidance augments them with usage semantics rather than replacing them.
- The same guidance contract should be available anywhere a tool entry is
  exposed from the catalog so discovery and inspection do not diverge.
- [auto] Recommended default selected: keep the guidance machine-readable and
  co-located with `_ToolSpec` / catalog output rather than introducing a second
  out-of-band reference surface.

### Example coverage is broad, but examples stay concise
- Every direct V3 CLI tool should expose at least one realistic common-path
  request example.
- Examples should use repo-consistent concrete placeholders such as
  `run-001`, `branch-001`, `primary`, and stable scenario labels rather than
  abstract pseudo-fields.
- Orchestration tools and commonly chained inspection or mutating tools should
  receive the most explicit examples because they anchor operator flow.
- Examples should remain concise enough to preserve the catalog as a discovery
  surface rather than turning it into a large handbook dump.
- [auto] Recommended default selected: cover the full direct-tool surface with
  one common-path example per tool, then let planning decide which tools need
  richer example annotations.

### Routing guidance stays aligned with the existing high-level surface
- Tool entries should make the routing layer explicit: when to use the direct
  tool, when not to use it, and which high-level skill is preferred instead.
- The current surface hierarchy remains locked: `rd-agent` is still the primary
  orchestration path, and direct tools remain the selective downshift layer.
- Routing guidance should reinforce the existing `category`,
  `subcategory`, and `recommended_entrypoint` contract instead of inventing a
  competing model.
- [auto] Recommended default selected: make routing guidance explicit per tool,
  but keep it subordinate to the existing skill-first public surface.

### Follow-up semantics must tell the operator what to do next
- Tool entries should state the expected next action after a successful call,
  especially when a tool produces a state transition, a shortlist, a selected
  branch, or a gated pause.
- Follow-up guidance should be outcome-oriented, for example "inspect branch
  state", "continue with `rd-agent`", or "hand off to the next stage skill",
  rather than implementation detail about internal services.
- Orchestration and gating-sensitive tools should explicitly explain paused or
  selected outcomes because these are the places agents most often stall.
- [auto] Recommended default selected: add structured follow-up semantics to
  every tool entry, with the strongest detail on orchestration tools and
  transition-driving primitives.

### Claude's Discretion
- Exact field names for examples, routing guidance, and follow-up semantics are
  left to planning as long as they are stable, machine-readable, and emitted by
  the public tool catalog.
- Planning may decide whether `list` and `describe` share the exact same
  payload shape or whether `describe` carries a superset, as long as discovery
  still exposes enough guidance to route correctly.

</decisions>

<specifics>
## Specific Ideas

- [auto] Selected all gray areas: guidance placement, example coverage, routing
  semantics, and follow-up semantics.
- Use Anthropic's advanced-tool-use lesson as the local product framing:
  schemas alone are insufficient; examples and usage patterns must be visible
  on the tool surface itself.
- Treat `rdagent-v3-tool describe <tool>` as the operator's canonical deep
  inspection path, but keep `list` useful enough for discovery and first-pass
  routing.
- Keep examples grounded in the existing standalone contracts instead of
  inventing aspirational inputs or hidden orchestration behaviors.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and phase truth
- `.planning/PROJECT.md` — v1.2 milestone goal, active requirements, and the
  constraint that guidance hardening must stay inside the existing V3 surface.
- `.planning/ROADMAP.md` — Phase 19 boundary and success criteria for tool
  catalog operator guidance.
- `.planning/REQUIREMENTS.md` — `GUIDE-01` through `GUIDE-03`, which define
  the direct-tool guidance outcomes this phase must satisfy.
- `.planning/STATE.md` — current phase position, blockers, and milestone-level
  sequencing decisions.

### Prior phase decisions that still apply
- `.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-CONTEXT.md`
  — locked decisions on skill-first routing, direct-tool categorization, and
  truthful public-surface language.
- `.planning/phases/18-standalone-packaging-and-planning-autonomy/18-CONTEXT.md`
  — locked decisions that keep the surface repo-local, transport-free, and
  separated from internal continuity guidance.

### Tool surface implementation anchors
- `v3/entry/tool_catalog.py` — central `_ToolSpec` registry and catalog-entry
  serialization for the public CLI tool surface.
- `v3/entry/tool_cli.py` — `rdagent-v3-tool list` / `describe` surface that
  emits catalog payloads to operators and agents.
- `skills/rd-tool-catalog/SKILL.md` — current decision-layer skill that routes
  callers between high-level skills and direct tools.

### Verification anchors
- `tests/test_v3_tool_cli.py` — direct CLI payload assertions for `list` and
  `describe`.
- `tests/test_phase16_tool_surface.py` — stable tool-surface coverage for the
  full direct-tool registry, categories, and schemas.
- `tests/test_phase13_v3_tools.py` — deeper schema and tool-surface assertions
  that will need to stay compatible with any new metadata fields.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `v3/entry/tool_catalog.py`: `_ToolSpec`, `_catalog_entry`, `list_cli_tools`,
  and `get_cli_tool` already centralize the public direct-tool metadata.
- `v3/entry/tool_cli.py`: already exposes `list` and `describe`, so new
  guidance can ride the existing CLI contract instead of requiring a new entry
  point.
- `skills/rd-tool-catalog/SKILL.md`: already defines the routing philosophy
  between high-level skills and direct tools and can stay aligned with the new
  catalog guidance.
- `tests/test_v3_tool_cli.py` and `tests/test_phase16_tool_surface.py`:
  existing regression anchors for catalog membership, routing metadata, and
  schema exposure.

### Established Patterns
- Public catalog payloads are machine-readable dictionaries with stable fields
  such as `category`, `subcategory`, `recommended_entrypoint`,
  `inputSchema`, and `outputSchema`.
- The standalone repo treats direct tools as a schema-described, transport-free
  downshift layer under high-level skill routing.
- Surface regressions are typically locked with focused, explicit payload
  assertions instead of screenshot-style or snapshot-style golden files.

### Integration Points
- New guidance fields will need to thread through `_ToolSpec`,
  `_catalog_entry`, `list_cli_tools`, and `get_cli_tool` together.
- CLI regression tests should assert the new guidance contract directly instead
  of inferring it from prose descriptions.
- Phase 19 should avoid broad README or stage-skill edits except where a tool
  surface change requires a narrowly scoped public-surface mention; the larger
  narrative and stage-skill contract work belongs to later phases.

</code_context>

<deferred>
## Deferred Ideas

- Stage-skill minimal-input contracts and pause/continue semantics belong to
  Phase 20.
- README narrative changes and broad public-surface regression updates belong
  to Phase 21.
- Machine-readable operator playbooks and richer multi-branch example sequences
  belong to later guidance-expansion work beyond this phase.

</deferred>

---

*Phase: 19-tool-catalog-operator-guidance*
*Context gathered: 2026-03-22*
