# Phase 21: Executable Public Surface Narrative - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase turns the already-hardened skill and tool contracts into the stable
public narrative for the standalone V3 surface. It covers README flow design
and regression coverage so a developer or agent can follow a concrete start,
inspect, and continue path without reading source code. It does not add new
orchestration behavior, new tool metadata families, or new stage-skill
contracts beyond what Phases 19 and 20 already locked.

</domain>

<decisions>
## Implementation Decisions

### README main flow
- README should open with the default `rd-agent` path rather than starting from
  a catalog overview or a CLI-first reference.
- The public narrative should be organized as one executable mainline:
  `Start -> Inspect -> Continue`.
- Stage skills should appear inside the `Continue` step as the next-step
  branches the agent chooses when the run is already paused at one known stage.
- `rd-tool-catalog` should appear as the inspect/downshift path, not as an
  equal top-level entrypoint beside `rd-agent`.

### Inspect is a first-class step
- `Inspect` should be a first-class step in the README, not an aside or an
  appendix.
- README should state the decision rule for `Inspect`: use it when the agent
  needs to confirm the current state, the right next surface, or the exact
  continuation contract before moving on.
- The main inspect entrypoints should be:
  the relevant `SKILL.md` contract and `uv run rdagent-v3-tool describe <tool>`
  when a lower-level direct tool must be checked.
- README should explicitly say the agent should do this work for the user:
  inspect current state, identify the next valid step, and present it, rather
  than pushing the user into manual surface discovery.

### Example strategy for README
- README should contain one concrete main example that walks through
  `Start -> Inspect -> Continue`.
- That main example should foreground the recommended multi-branch path first.
- README must immediately add the balancing note that simpler tasks can take
  the single-branch minimum path instead of the richer multi-branch route.
- README should include one representative continue example, then route the
  reader to the individual `SKILL.md` files and `rdagent-v3-tool describe ...`
  for the exact field-level contract details.
- README should not become a second schema catalog or duplicate the full field
  inventory that already lives in skill packages and tool metadata.

### Regression scope for Phase 21
- Phase 21 tests should lock the executable narrative itself, not just section
  existence.
- Regression coverage should assert the README contains the `Start -> Inspect ->
  Continue` mainline, the `rd-agent`-first entrypoint, the inspect/downshift
  rule, and the continue handoff to stage skills.
- Regression coverage should explicitly lock the agent-first framing: README is
  written to help the agent help the user, not to force the user to manually
  research tools.
- Regression coverage should lock the relationship between the recommended
  multi-branch path and the simpler single-branch fallback for easy tasks.
- README regressions should also verify that the README still points to the
  real skill and tool surfaces, especially the `SKILL.md` files and
  `uv run rdagent-v3-tool describe ...` inspection path.

### Claude's Discretion
- Planning may choose whether the executable mainline lives in one dedicated
  README section or is distributed across a few adjacent sections, as long as
  the flow still reads clearly as `Start -> Inspect -> Continue`.
- Planning may choose the exact example payload values and wording as long as
  the example remains grounded in the real Phase 19/20 contracts and does not
  drift into aspirational behavior.

</decisions>

<specifics>
## Specific Ideas

- Treat README as an agent-first playbook:
  the agent reads the public narrative and then helps the user run it, rather
  than the user being expected to study the whole surface directly.
- The inspect step should explicitly answer:
  "Do I stay in `rd-agent`, continue with a stage skill, or inspect a direct
  tool contract first?"
- The README example should lead with the richer multi-branch path because that
  better represents the default orchestration story, but it should immediately
  add the single-branch note so the public surface does not imply unnecessary
  complexity for small tasks.
- Keep README narrow and executable:
  one main path, one continue example, and explicit links outward for detailed
  field contracts.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase and milestone truth
- `.planning/PROJECT.md` — v1.2 milestone goal and the product requirement that
  the public surface become executable from guidance rather than source-code
  spelunking.
- `.planning/ROADMAP.md` — Phase 21 boundary and the `SURFACE-01` /
  `SURFACE-02` success criteria for the public narrative.
- `.planning/REQUIREMENTS.md` — `SURFACE-01` and `SURFACE-02`, which Phase 21
  must satisfy.
- `.planning/STATE.md` — current milestone position and the sequencing note
  that README/test locking comes after the Phase 19/20 contract hardening.

### Prior phase decisions that still apply
- `.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-CONTEXT.md`
  — locked decisions on `rd-agent` first, skill/CLI routing order, and README
  as the public surface narrative.
- `.planning/phases/19-tool-catalog-operator-guidance/19-CONTEXT.md` — locked
  decisions on examples, routing guidance, follow-up semantics, and keeping
  direct tools subordinate to the high-level skill path.
- `.planning/phases/20-stage-skill-execution-contracts/20-CONTEXT.md` — locked
  decisions on `rd-agent` minimum vs recommended start paths, plain-language
  pause semantics, stage-skill continuation contracts, and agent-led missing-
  field recovery.

### Current public narrative and regression anchors
- `README.md` — current public narrative that now needs to become an explicit
  `Start -> Inspect -> Continue` playbook.
- `tests/test_phase17_surface_convergence.py` — current README regression file
  that proves section existence but not yet the executable public narrative.
- `tests/test_phase18_planning_continuity.py` — current regression that keeps
  README public-only and keeps internal continuity out of the public doc.

### Current public skill and tool surfaces
- `skills/rd-agent/SKILL.md` — current default orchestration contract with the
  minimum start path and default pause explanation.
- `skills/rd-propose/SKILL.md` — continuation contract for the first continue
  branch inside the README flow.
- `skills/rd-code/SKILL.md` — continuation contract for the build-step branch.
- `skills/rd-execute/SKILL.md` — continuation contract for verification and the
  blocked path.
- `skills/rd-evaluate/SKILL.md` — continuation contract for continue vs stop at
  synthesize.
- `skills/rd-tool-catalog/SKILL.md` — decision-layer downshift path that
  README should present as subordinate to the high-level mainline.
- `v3/entry/tool_cli.py` — current `rdagent-v3-tool list` / `describe` public
  entrypoint that README should cite for inspect/downshift behavior.
- `tests/test_v3_tool_cli.py` — public tool-surface assertions already locking
  the structured operator guidance fields.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `README.md` already has the major public sections:
  orchestration, stage skills, tool catalog, routing model, and verification.
  Phase 21 can refactor this into one executable mainline instead of writing a
  new public document from scratch.
- `skills/rd-agent/SKILL.md` already provides the minimum start contract,
  recommended multi-branch path, and default stop semantics that README can
  summarize instead of re-specifying in full detail.
- The four stage-skill `SKILL.md` files already provide a shared continue
  contract surface and exact stage-specific deltas, so README can link to them
  instead of duplicating all continuation fields.
- `rdagent-v3-tool describe <tool>` already exposes examples, routing guidance,
  and follow-up semantics, which makes it a natural inspect/downshift step in
  the README flow.

### Established Patterns
- Public surface regressions in this repo are file-reading tests with explicit
  string assertions rather than snapshots.
- README is treated as a public document and `.planning/STATE.md` is treated as
  internal continuity truth; Phase 21 must preserve that split.
- High-level skills are the main operator surface, and direct tools are a
  selective downshift layer beneath them.

### Integration Points
- README changes and README regressions must move together in the same phase so
  the public narrative cannot drift away from the real skill and tool surface.
- Phase 21 should reuse the exact public command forms already present in the
  repo, such as `uv run rdagent-v3-tool describe rd_run_start`, rather than
  inventing a new inspect command path.
- Any new README wording about start/continue flows should stay aligned with
  the specific contracts already locked in the Phase 20 skill docs.

</code_context>

<deferred>
## Deferred Ideas

- Any attempt to add new orchestration helpers, new CLI entrypoints, or new
  public transport abstractions belongs to a later phase.
- A machine-readable operator playbook generator belongs to later work under
  `SURFACE-03`, not this README-and-regression locking phase.
- Any broader restructuring of the product surface beyond the README and its
  regressions belongs to later roadmap work.

</deferred>

---

*Phase: 21-executable-public-surface-narrative*
*Context gathered: 2026-03-22*
