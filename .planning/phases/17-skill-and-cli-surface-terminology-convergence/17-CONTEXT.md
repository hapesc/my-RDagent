# Phase 17: Skill and CLI Surface Terminology Convergence - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the standalone V3 public surface honest and consistent as a
skill-plus-CLI model. It covers terminology convergence, real skill package
creation, CLI tool classification, and README/test alignment for the existing
surface. It does not add new orchestration capabilities, install/runtime
mechanisms, or deeper contract changes.

</domain>

<decisions>
## Implementation Decisions

### Skill surface realization
- Phase 17 will create real agent-facing skill packages instead of only
  renaming docs to say "skills".
- The skill surface is primarily for agent invocation, not human-first manual
  documentation.
- This phase should deliver the complete minimum skill set needed for the
  public surface to be truthful, not a placeholder subset.
- Every new or refactored skill in this phase must be created through
  `$skill-architect`.
- Skill package contents and whether each skill needs `references/`,
  `assets/`, or `scripts/` are delegated to `$skill-architect` rather than
  being pre-decided in the phase context.

### Skill hierarchy and routing
- Skill names should align directly with existing entrypoint names to avoid
  product/code drift.
- The core skill set should include `rd-agent`, `rd-propose`, `rd-code`,
  `rd-execute`, `rd-evaluate`, and `rd-tool-catalog`.
- `rd-agent` is the primary orchestration entrypoint for the public surface.
- High-level skills are the default entrypoints. Agents should only drop to
  primitive CLI tools when the high-level skill boundary is insufficient.
- All `rd-*` skills must state three boundaries clearly:
  when to use the skill, when to route to `rd-tool-catalog`, and when not to
  use the skill.
- Whether a thin routing skill is needed should be decided by
  `$skill-architect`, not assumed up front.

### CLI tool categorization
- `rd-tool-catalog` is a decision-oriented skill, not a passive reference page.
- The top-level CLI tool categories are `orchestration`, `inspection`, and
  `primitives`.
- The `primitives` category must have stable second-level categorization so
  agents can narrow the search space before choosing a specific tool.
- CLI outputs should carry stable structured classification fields so skills
  and tests do not need to infer categories from prose.
- Tool selection guidance should default to:
  stay in high-level skills unless needed, then narrow by category before
  selecting a specific primitive tool.
- How strongly to emphasize round tools such as `rd_explore_round` and
  `rd_converge_round` inside `rd-tool-catalog` should be decided by
  `$skill-architect` during skill design.
- `rd-tool-catalog` must also say when not to drop to primitives.

### Phase 17 delivery boundary
- Phase 17 includes terminology convergence, real skill packages, catalog
  classification, and README/test synchronization.
- Phase 17 may adjust surface-layer code such as `tool_catalog.py`, CLI output,
  README, tests, and skill package structure.
- Phase 17 must not change lower-level orchestration, contract, or runtime
  semantics.
- Tests should be updated to reflect the new public surface model rather than
  only adding existence smoke checks.

### README and public narrative
- README should present `rd-agent` first as the default entrypoint.
- Remaining skills should be introduced in the order an agent would normally
  use them, then the CLI tool catalog should be described as the selective
  downshift layer.
- README should state the global routing model and the shared contract used by
  all `rd-*` skills.
- README should mention "`$skill-architect` first" in a skill-authoring section
  rather than in the main operator path.
- README should explain the CLI layer with category guidance plus a small
  number of `list` / `describe` examples, not a full catalog dump.

### Claude's Discretion
- Exact folder layout and package internals for each skill are left to
  `$skill-architect`.
- Whether to include a thin routing skill is left to `$skill-architect`.
- The precise naming and placement of primitive subcategories are flexible as
  long as they preserve the locked top-level classification and stable machine-
  readable fields.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and requirement truth
- `.planning/PROJECT.md` — Current standalone V3 product positioning,
  milestone goal, active requirements, and non-negotiable constraints.
- `.planning/ROADMAP.md` — Phase 17 boundary, milestone framing, and success
  criteria for terminology convergence.
- `.planning/REQUIREMENTS.md` — `SURFACE-01` through `SURFACE-03` definitions
  that this phase must satisfy.
- `.planning/STATE.md` — Current session state and explicit "plan Phase 17"
  continuation note.

### Existing surface and code anchors
- `README.md` — Current public narrative that must be rewritten to match the
  real skill-plus-CLI surface.
- `v3/entry/rd_agent.py` — Current primary orchestration entrypoint that should
  stay the top-level skill anchor.
- `v3/entry/tool_catalog.py` — Current CLI tool catalog surface that needs
  explicit public classification.
- `v3/entry/tool_cli.py` — Current CLI entrypoint and output shape for
  `rdagent-v3-tool`.

### Current verification and historical framing
- `.planning/V3-EXTRACTION-HANDOFF.md` — Extraction decisions that replaced the
  old MCP-shaped surface with a CLI-oriented catalog.
- `.planning/phases/16-multi-branch-orchestration-and-tool-surface-completion/16-VERIFICATION.md`
  — Most recent proof of the current tool surface and related tests.

### External design inspirations captured locally
- `.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-EXTERNAL-REFERENCES.md`
  — Repo-local summary of the external skill-set and tool-use references cited
  during discussion, including GSD, Superpowers, and Anthropic's advanced tool
  use article.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `v3/entry/rd_agent.py`: already acts as the orchestration entrypoint spanning
  single-branch and multi-branch behavior; this should anchor the main skill.
- `v3/entry/rd_propose.py`, `v3/entry/rd_code.py`, `v3/entry/rd_execute.py`,
  `v3/entry/rd_evaluate.py`: existing stage-specific entrypoints that naturally
  map to specialized skills.
- `v3/entry/tool_catalog.py`: already centralizes tool specs and is the natural
  place to add stable category metadata.
- `v3/entry/tool_cli.py`: already provides `list` and `describe`; it can expose
  new classification fields without changing lower-level behavior.
- `tests/test_v3_tool_cli.py`: current CLI assertions provide the starting point
  for public-surface output expectations.
- `tests/test_phase16_tool_surface.py`: current catalog membership and schema
  assertions provide the starting point for classification-aware surface tests.

### Established Patterns
- Public V3 entrypoints are thin wrappers over V3-owned orchestration/services
  rather than runtime-specific adapters.
- The CLI catalog is schema-described and transport-free; the phase should
  extend this pattern rather than introducing transport/server abstractions.
- Surface truth is already verified through focused public-surface tests, so
  Phase 17 should keep that verification style and retarget it to the new model.

### Integration Points
- New skill packages will need to align with the current V3 entrypoint names and
  be referenced from README and planning artifacts.
- Tool classification changes should thread through catalog metadata, CLI
  output, README narrative, and tests together.
- `$skill-architect` will define per-skill package structure, but the phase plan
  must reserve work for both skill creation and catalog/document/test updates.

</code_context>

<specifics>
## Specific Ideas

- Use the `gsd-build/get-shit-done` repository as the reference for "clear main
  workflow entrypoint plus named specialized commands", not for copying its full
  project-management skill surface.
- Use `obra/superpowers` as the reference for flat, discoverable, single-purpose
  skills and for the idea that a thin guidance skill may exist when it improves
  routing clarity.
- Use Anthropic's "Advanced tool use" article as the reference for on-demand
  tool discovery, keeping higher-level orchestration above primitive tool calls,
  and making usage guidance as important as schemas.
- Treat "create or refactor a skill via `$skill-architect`" as a public authoring
  rule for this repo, but place it in the README's skill-authoring section rather
  than in the default operator path.

</specifics>

<deferred>
## Deferred Ideas

- Whether the standalone repo should eventually ship skill installation or skill
  discovery/runtime support beyond repo-local package structure belongs to a
  later phase.
- Any broader packaging or autonomy work beyond the Phase 17 surface layer
  belongs in Phase 18.

</deferred>

---

*Phase: 17-skill-and-cli-surface-terminology-convergence*
*Context gathered: 2026-03-21*
