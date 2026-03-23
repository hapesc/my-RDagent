# Phase 19: Tool Catalog Operator Guidance - Research

**Researched:** 2026-03-22
**Domain:** standalone V3 tool-catalog operator guidance
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Guidance lives in structured tool metadata
- The new operator guidance must live in the structured data emitted by the V3
  tool catalog, not only in prose-only docs or skill references.
- `inputSchema` and `outputSchema` remain the structural contract; the new
  guidance augments them with usage semantics rather than replacing them.
- The same guidance contract should be available anywhere a tool entry is
  exposed from the catalog so discovery and inspection do not diverge.

### Example coverage is broad, but examples stay concise
- Every direct V3 CLI tool should expose at least one realistic common-path
  request example.
- Examples should use repo-consistent placeholders such as `run-001`,
  `branch-001`, `primary`, and stable scenario labels.
- Orchestration tools and commonly chained inspection or mutating tools should
  receive the most explicit examples because they anchor operator flow.
- Examples should stay concise enough for discovery usage rather than becoming
  a giant handbook dump.

### Routing guidance stays aligned with the existing high-level surface
- Tool entries should say when to use the direct tool, when not to use it, and
  which high-level skill is preferred instead.
- `rd-agent` remains the primary orchestration path and direct tools remain the
  selective downshift layer.
- Routing guidance should reinforce `category`, `subcategory`, and
  `recommended_entrypoint` rather than inventing a competing model.

### Follow-up semantics must tell the operator what to do next
- Tool entries should state the expected next action after a successful call,
  especially when a tool produces a state transition, a shortlist, a selected
  branch, or a gated pause.
- Follow-up guidance should be outcome-oriented rather than implementation
  detail about internal services.
- Orchestration and gating-sensitive tools need the strongest next-step
  guidance because these are where agents most often stall.

### Claude's Discretion
- Exact field names are flexible as long as they are stable, machine-readable,
  and emitted by the public tool catalog.
- Planning may choose whether `list` and `describe` share the exact same
  payload shape or whether `describe` is a strict superset.

### Deferred Ideas (OUT OF SCOPE)
- Stage-skill minimal-input contracts and pause/continue semantics belong to
  Phase 20.
- README narrative changes and broad public-surface regression updates belong
  to Phase 21.
- Machine-readable operator playbooks and richer multi-branch example sequences
  belong to later guidance-expansion work.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUIDE-01 | Developer can inspect a direct V3 CLI tool and see one or more concrete request examples with realistic arguments for the common path. | Add a structured examples field to the catalog entry model and surface it through `list_cli_tools()` / `get_cli_tool()`, with at least one common-path example per tool. |
| GUIDE-02 | Developer can inspect a direct V3 CLI tool and see when to use it, when not to use it, and which higher-level skill is preferred when the direct tool is the wrong layer. | Add stable routing-guidance fields that complement `recommended_entrypoint` and align with the existing skill-first surface. |
| GUIDE-03 | Developer can inspect a direct V3 CLI tool and understand the expected follow-up action after a successful call, especially for orchestration and gated-stop results. | Add structured next-step semantics on the catalog entry, with the richest guidance on orchestration and transition-driving tools. |
</phase_requirements>

## Summary

Phase 19 is a metadata-and-verification phase, not a behavior phase. The
lowest-risk implementation seam is `v3/entry/tool_catalog.py`, because that
module already owns `_ToolSpec`, `_catalog_entry`, `list_cli_tools()`, and
`get_cli_tool()`. `v3/entry/tool_cli.py` is only a thin JSON transport layer,
so changing the operator guidance should happen in the catalog entry shape and
flow through the existing CLI unchanged.

The repo already has strong regression anchors around the tool surface:
`tests/test_v3_tool_cli.py` checks the public CLI payloads, and
`tests/test_phase16_tool_surface.py` checks catalog membership, categories, and
schemas. That means Phase 19 should lock the new guidance with explicit field
assertions instead of prose-only docs. The planner does not need to invent a
new surface; it needs to enrich the current one in a way that remains truthful,
machine-readable, and compatible with the existing schema-driven contract.

**Primary recommendation:** implement Phase 19 in three slices:
1. Extend `_ToolSpec` and catalog serialization with structured examples,
   routing guidance, and follow-up semantics.
2. Populate the full direct-tool surface with one common-path example per tool,
   while giving orchestration and chaining-heavy tools more explicit next-step
   guidance.
3. Add a Phase 19 regression suite plus targeted updates to existing tool
   surface tests so the new guidance contract cannot regress silently.

## Current Surface Findings

### Finding 1: `_ToolSpec` is the single source of tool metadata truth
- `v3/entry/tool_catalog.py` defines `_ToolSpec` with the current public fields:
  name, title, description, category, subcategory, recommended entrypoint, and
  schema models.
- `_catalog_entry()` already materializes these fields into the JSON returned by
  `list_cli_tools()` and `get_cli_tool()`.
- This is the cleanest place to add new guidance without spreading logic across
  CLI parsing, README prose, and tests.

### Finding 2: `list` and `describe` currently share the same payload model
- `v3/entry/tool_cli.py` simply forwards the payload returned by
  `list_cli_tools()` or `get_cli_tool()`.
- `list` currently emits full `inputSchema` / `outputSchema`, so the catalog is
  already comfortable returning rich structured metadata.
- Adding concise examples and guidance to the same payload family is aligned
  with the current surface; it is not a conceptual break.

### Finding 3: Existing skill guidance and tool guidance are separated
- `skills/rd-tool-catalog/SKILL.md` explains the routing philosophy, but the
  direct tools themselves only expose schemas and category metadata.
- This is exactly the stall point surfaced in recent `rd-agent` usage:
  structurally valid tools still lack usage semantics on the tool layer.
- Phase 19 should close that gap without stealing Phase 20’s stage-skill work.

### Finding 4: Existing tests are field-level, not snapshot-level
- `tests/test_v3_tool_cli.py` and `tests/test_phase16_tool_surface.py` use
  explicit assertions on payload fields and schemas.
- That pattern is a good fit for Phase 19 because it makes the public contract
  obvious and keeps failures surgical when guidance fields drift.

## Recommended Patterns

### Pattern 1: Structured Example Objects
**What:** each tool entry exposes a short list of example objects rather than a
single prose blob.
**Why:** examples need to stay machine-readable and checkable.
**Recommended shape:** each example should at least identify the common path,
use concrete arguments, and optionally include a short note about why that
example is representative.
**Where:** `_ToolSpec` metadata and `_catalog_entry()` output.

### Pattern 2: Routing Guidance Adjacent to `recommended_entrypoint`
**What:** add explicit guidance for `when_to_use`, `when_not_to_use`, and the
preferred high-level path when the direct tool is the wrong layer.
**Why:** `recommended_entrypoint` alone is too thin; it tells the caller who is
preferred, but not the decision boundary.
**Where:** tool-catalog payload, not just `skills/rd-tool-catalog/SKILL.md`.

### Pattern 3: Follow-Up Guidance as Outcome Semantics
**What:** add a field that states the expected next action after a successful
call.
**Why:** agents currently stall after a successful tool call because success
does not imply a next action.
**Examples of useful follow-up semantics:**
- `rd_run_start` → continue with `rd-agent` or inspect the returned branch/stage
- `rd_explore_round` → inspect branch board or continue toward convergence
- `rd_branch_select_next` → continue work on the selected branch
- `rd_recovery_assess` → rebuild artifacts or continue to the next stage based
  on the recovery result

### Pattern 4: Concise Coverage for the Full Tool Surface
**What:** provide one example per direct tool, not only for orchestration.
**Why:** the requirement is phrased around inspecting a direct V3 CLI tool, not
  a cherry-picked subset.
**Tradeoff:** keep examples short enough that the catalog remains readable.

## Likely Plan Slices

1. Extend tool metadata and serialization
   - update `_ToolSpec`
   - add new public guidance fields in `_catalog_entry()`
   - keep existing schema/category fields unchanged

2. Populate examples and guidance across the registry
   - define one common-path example per tool
   - prioritize richer follow-up notes for orchestration and mutating tools
   - ensure examples use repo-consistent placeholder IDs

3. Lock the guidance contract with tests
   - extend CLI payload assertions
   - extend phase16 tool-surface assertions
   - add a focused Phase 19 test file for examples/routing/follow-up behavior

## Anti-Patterns to Avoid

- **Docs-only examples:** putting examples only in README or `references/`
  leaves the tool layer unchanged and fails the requirement.
- **Overly verbose catalog entries:** turning each tool entry into a handbook
  will make discovery harder and bloat `list` output.
- **Phase 20 leakage:** do not solve stage-skill minimal-input contracts here.
- **Behavior creep:** do not change orchestration semantics just to make
  examples easier to write.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| example reference surface | separate prose handbook | structured examples in `_ToolSpec` | one source of truth keeps list/describe/tests aligned |
| routing explanation | infer from descriptions | explicit routing guidance fields | stable fields are easier for agents and tests to consume |
| next-step discovery | rely on source inspection | structured follow-up semantics | operators need to know what to do after success |
| large snapshot tests | opaque JSON snapshots | explicit field assertions | failures stay readable and targeted |

## Common Pitfalls

### Pitfall 1: Examples only for orchestration tools
**What goes wrong:** `rd_run_start` and `rd_explore_round` get examples, but
inspection and primitive tools still require guesswork.
**How to avoid:** make "one common-path example per direct tool" a plan-level
acceptance rule.

### Pitfall 2: Routing guidance duplicates skill docs without adding tool value
**What goes wrong:** the tool payload simply repeats `recommended_entrypoint`
in prose and still does not tell the caller when to downshift.
**How to avoid:** state the decision boundary explicitly in the tool payload.

### Pitfall 3: Follow-up guidance is too implementation-specific
**What goes wrong:** tool metadata talks about internal services rather than
operator-visible next actions.
**How to avoid:** phrase follow-up semantics as the next tool or skill action.

### Pitfall 4: Test coverage only checks field presence
**What goes wrong:** fields exist but carry empty or useless values.
**How to avoid:** tests should assert non-empty examples, stable routing hints,
and meaningful follow-up content for representative tools.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest >=7.4.0` |
| Config file | `pyproject.toml` |
| Quick run command | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q` |
| Full suite command | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q` |
| Estimated runtime | ~15 seconds |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUIDE-01 | every direct tool entry exposes at least one realistic common-path example | unit/public-surface | `uv run python -m pytest tests/test_phase19_tool_guidance.py -q` | `tests/test_phase19_tool_guidance.py` ❌ Wave 0 |
| GUIDE-02 | direct tool entries expose explicit routing boundaries beyond `recommended_entrypoint` | unit/public-surface | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase19_tool_guidance.py -q` | `tests/test_v3_tool_cli.py` ✅ / `tests/test_phase19_tool_guidance.py` ❌ Wave 0 |
| GUIDE-03 | direct tool entries expose expected next-step semantics after success | unit/public-surface | `uv run python -m pytest tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q` | `tests/test_phase16_tool_surface.py` ✅ / `tests/test_phase19_tool_guidance.py` ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q`
- **Per wave merge:** `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_guidance.py -q`
- **Before phase verification:** full suite above must be green

