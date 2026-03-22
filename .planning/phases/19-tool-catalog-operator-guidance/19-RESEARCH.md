# Phase 19: Tool Catalog Operator Guidance - Research

**Researched:** 2026-03-22
**Domain:** direct V3 CLI tool metadata, routing guidance, and operator follow-up semantics
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

### Deferred Ideas (OUT OF SCOPE)
- Stage-skill minimal-input contracts and pause/continue semantics belong to
  Phase 20.
- README narrative changes and broad public-surface regression updates belong
  to Phase 21.
- Machine-readable operator playbooks and richer multi-branch example sequences
  belong to later guidance-expansion work beyond this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUIDE-01 | Developer can inspect a direct V3 CLI tool and see one or more concrete request examples with realistic arguments for the common path. | Add one concise, machine-readable example per `_ToolSpec`, emitted from the public catalog as a sibling to `inputSchema`/`outputSchema`; reuse repo-established literals like `run-001`, `branch-001`, `memory-001`, `data_science`, and stage keys from existing tests. |
| GUIDE-02 | Developer can inspect a direct V3 CLI tool and see when to use it, when not to use it, and which higher-level skill is preferred when the direct tool is the wrong layer. | Preserve `category`, `subcategory`, and `recommended_entrypoint` as the routing spine, and add explicit per-tool routing semantics that explain those fields rather than replacing them. |
| GUIDE-03 | Developer can inspect a direct V3 CLI tool and understand the expected follow-up action after a successful call, especially for orchestration and gated-stop results. | Add outcome-oriented follow-up metadata per tool, with strongest detail on `rd_run_start`, `rd_explore_round`, `rd_converge_round`, `rd_recovery_assess`, `rd_branch_select_next`, shortlist/merge/fallback tools, and other state-transitioning primitives. |
</phase_requirements>

## Summary

Phase 19 is a metadata-hardening phase, not a runtime-contract phase. The
direct tool surface already has a single source of truth in
`v3/entry/tool_catalog.py`: `_ToolSpec` defines every public tool entry, and
both `list_cli_tools()` and `get_cli_tool()` serialize through the same
`_catalog_entry()` function. `v3/entry/tool_cli.py` is only a thin `argparse`
wrapper over those functions. That means the safest implementation path is to
extend `_ToolSpec` with guidance metadata and emit it from `_catalog_entry()`
once, rather than creating a second registry, a docs-only layer, or per-command
custom serializers.

The biggest planning constraint is the existing schema contract. Current tests
assert that `inputSchema` and `outputSchema` equal exact
`model_json_schema()` output for many tools. Because of that, examples and
operator guidance should not be injected into the Pydantic schemas themselves.
They should be sibling metadata fields in the catalog payload. This preserves
the schema-driven surface while satisfying the Phase 19 requirement that the
guidance stay machine-readable and co-located with the catalog.

The direct-tool surface is broad but manageable: `tests/test_phase16_tool_surface.py`
locks a 23-tool registry today, split across 3 orchestration tools, 10
inspection tools, and 10 primitive tools. One realistic common-path example
per tool is feasible if the plan uses a shared placeholder vocabulary and
groups authoring by category. The strongest follow-up guidance should be
reserved for the tools whose current result contracts already expose next-step
signals or state transitions; README and stage-skill contract work remain out
of scope for this phase.

**Primary recommendation:** add a stable machine-readable guidance block to
`_ToolSpec` and `_catalog_entry()`, keep `list` and `describe` aligned through
the same serializer, and lock the new surface with one new Phase 19 test file
plus focused extensions to the existing CLI and registry regressions.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.11` | runtime for the tool catalog, CLI, and tests | fixed by `pyproject.toml`; no new runtime is needed |
| `pydantic` | `>=2,<3` | `model_json_schema()` source for `inputSchema`/`outputSchema` | already defines the structural contract the catalog exposes |
| `argparse` | stdlib | `rdagent-v3-tool` CLI surface | current CLI is intentionally thin and stable |
| `v3.entry.tool_catalog` | repo-local | canonical registry for public direct-tool metadata | all list/describe payloads already flow through this module |
| `skills/rd-tool-catalog` | repo-local | current routing philosophy for high-level skills vs direct tools | Phase 19 guidance should align with, not compete with, this skill |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=7.4.0` | public-surface regression tests | for CLI payload, registry coverage, and new guidance assertions |
| `import-linter` | `>=2.3,<3.0` | boundary gate | at the phase gate to ensure metadata work does not leak legacy imports |
| README quick/full gate commands | repo-local convention | existing operator validation flow | keep phase validation aligned with the documented repo workflow |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| extending `_ToolSpec` and `_catalog_entry()` | separate docs/JSON registry | creates drift between the public catalog and the source of truth |
| sibling guidance fields | embedding examples inside `inputSchema` / `outputSchema` | would blur structure vs guidance and collide with exact schema assertions |
| shared `list` / `describe` serializer | custom `describe`-only shape | allows richer payloads but introduces divergence risk and more tests |

**Version verification:** the relevant versions are already pinned or bounded in
`pyproject.toml` and `uv.lock`. No new third-party dependency is required for
Phase 19.

## Architecture Patterns

### Recommended Project Structure
```text
v3/
├── entry/
│   ├── tool_catalog.py         # extend _ToolSpec and _catalog_entry once
│   └── tool_cli.py             # keep as thin wrapper over list/describe
└── contracts/
    ├── tool_io.py              # source of request/response shapes
    ├── recovery.py             # existing recommended_next_step signal
    └── run.py                  # execution_mode / paused-state vocabulary

skills/
└── rd-tool-catalog/
    ├── SKILL.md                # optional narrow alignment only
    └── references/tool-selection.md

tests/
├── test_v3_tool_cli.py
├── test_phase16_tool_surface.py
├── test_phase13_v3_tools.py
└── test_phase19_tool_catalog_guidance.py
```

### Pattern 1: Extend the Single Public Serializer
**What:** add guidance fields to `_ToolSpec` and emit them from
`_catalog_entry()`, so both `list_cli_tools()` and `get_cli_tool()` stay aligned.
**When to use:** for every new example, routing rule, or follow-up semantic.
**Why:** current `list` and `describe` already share the same payload source, so
one serializer update avoids discovery/inspection drift.

### Pattern 2: Keep Guidance Outside the Schemas
**What:** store examples and operator semantics alongside `inputSchema` and
`outputSchema`, not inside them.
**When to use:** always in this phase.
**Why:** `tests/test_phase13_v3_tools.py` and `tests/test_phase16_tool_surface.py`
assert exact schema equality against Pydantic models. Adding guidance inside
schemas would change the structural contract instead of augmenting it.

### Pattern 3: Use a Shared Placeholder Vocabulary
**What:** standardize example values across tools around stable literals:
`run-001`, `branch-001`, `branch-002`, `memory-001`, `primary`,
`data_science`, `framing`, and `verify`.
**When to use:** for all common-path examples.
**Why:** these values already appear in current tests and context files, so they
will read as realistic and repo-native rather than invented.

### Pattern 4: Follow-Up Semantics Should Describe Operator Action
**What:** guidance should answer "what do I do next?" after a successful call,
not restate implementation internals.
**When to use:** especially for orchestration and selection/gating-sensitive
tools.
**Why:** several current result models already expose next-step signals:
- `RecoveryAssessment.recommended_next_step`
- `BranchSelectNextRecommendation.recommended_next_step`
- `ExploreRoundResult.recommended_next_step`
- `ConvergeRoundResult.recommended_next_step`

Catalog guidance should explain how an operator uses those outcomes, for
example "inspect the selected branch", "continue via `rd-agent`", or "review
the shortlist before merge/fallback".

### Pattern 5: Prefer One Stable Guidance Block
**What:** keep guidance machine-readable under one stable field family rather
than scattering many unrelated top-level strings.
**When to use:** when choosing the final payload shape.
**Recommended shape:**
```python
guidance = {
    "examples": [{"label": "common_path", "arguments": {...}}],
    "routing": {
        "use_when": "...",
        "avoid_when": "...",
        "preferred_skill": "rd-agent",
    },
    "follow_up": {
        "on_success": "...",
        "inspect_with": "rd_run_get",
        "continue_with": "rd-agent",
    },
}
```
**Why:** this preserves the existing routing spine at the top level
(`category`, `subcategory`, `recommended_entrypoint`) while giving planners a
cohesive place to add Phase 19 semantics.

### Anti-Patterns to Avoid
- **Schema mutation for guidance:** do not push examples into Pydantic schema
  extras just because the catalog already exposes schemas.
- **Docs-only truth:** README or `SKILL.md` may align later, but the tool
  catalog itself must carry the guidance contract in this phase.
- **List/describe drift:** do not let `describe` become the only place with
  real guidance unless the plan also defines how `list` remains enough for
  discovery.
- **Aspirational examples:** do not publish examples that imply Phase 20
  stage-skill contracts or Phase 21 narrative workflows.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| tool guidance source | a second YAML/JSON/doc registry | `_ToolSpec` in `v3.entry.tool_catalog` | existing list/describe payloads already derive from it |
| routing explanation | heuristics inferred from prose or category names | explicit machine-readable routing metadata aligned with `recommended_entrypoint` | keeps the direct-tool surface truthful and testable |
| common-path examples | schema-only auto-generation | curated examples using current request fields and repo-native literals | schema shape alone cannot tell the operator the realistic happy path |
| regression strategy | large snapshots or golden JSON dumps | focused pytest assertions on required fields and representative tools | matches current repo testing style and avoids brittle catalog snapshots |

**Key insight:** Phase 19 should harden the current catalog contract, not create
another guidance layer around it.

## Common Pitfalls

### Pitfall 1: Breaking the schema-driven surface while trying to improve it
**What goes wrong:** examples or routing text get embedded into `inputSchema` or
`outputSchema`, changing structural payloads.
**Why it happens:** the catalog already exposes schemas, so it is tempting to
reuse that channel for guidance.
**How to avoid:** keep all Phase 19 additions as sibling metadata fields.
**Warning signs:** changes to `model_json_schema()` output or failing exact
equality assertions in `tests/test_phase13_v3_tools.py`.

### Pitfall 2: Divergent `list` and `describe` semantics
**What goes wrong:** `describe` gets useful guidance but `list` remains too thin
to support first-pass routing, or the two commands expose different field names.
**Why it happens:** adding a special case to `get_cli_tool()` is easy.
**How to avoid:** keep one shared serializer unless there is a strong, explicit
reason to introduce a `describe` superset.
**Warning signs:** separate serialization branches or tests that duplicate the
same expectations in different shapes.

### Pitfall 3: Publishing unrealistic examples
**What goes wrong:** examples use abstract placeholders or arguments that do not
match the current contracts.
**Why it happens:** manual example authoring gets treated as documentation
copywriting instead of interface design.
**How to avoid:** derive field names from `v3/contracts/tool_io.py` and values
from existing test fixtures and phase context.
**Warning signs:** examples that mention nonexistent fields, Phase 20 stage
payloads, or hidden orchestration behaviors.

### Pitfall 4: Overreaching into later phases
**What goes wrong:** planning starts rewriting README, stage skills, or
operator playbooks because guidance work feels narrative-adjacent.
**Why it happens:** the milestone itself spans tool metadata, skill contracts,
and public docs.
**How to avoid:** keep Phase 19 limited to direct tool metadata plus only the
minimum narrow alignment needed to keep repo guidance truthful.
**Warning signs:** plan steps centered on `README.md`, `rd-agent` minimal input
contracts, or stage continuation payloads.

### Pitfall 5: Under-specifying follow-up semantics for the tools that matter most
**What goes wrong:** every tool gets the same generic "inspect state" note, so
operators still stall after orchestration or branch-selection actions.
**Why it happens:** planners optimize for uniformity instead of operational
value.
**How to avoid:** give extra detail to tools that already expose selected
branch IDs, shortlists, merge outcomes, or `recommended_next_step`.
**Warning signs:** `rd_explore_round`, `rd_converge_round`, `rd_recovery_assess`,
and `rd_branch_select_next` all end up with indistinguishable follow-up text.

## Code Examples

Verified patterns from current repo sources:

### Single-source catalog serialization
```python
# Source: v3/entry/tool_catalog.py
def _catalog_entry(spec: _ToolSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "title": spec.title,
        "description": spec.description,
        "surface": "cli_tool",
        "category": spec.category,
        "subcategory": spec.subcategory,
        "recommended_entrypoint": spec.recommended_entrypoint,
        "command": f"rdagent-v3-tool describe {spec.name}",
        "inputSchema": spec.request_model.model_json_schema(),
        "outputSchema": spec.response_model.model_json_schema(),
    }
```

### Focused public-surface assertions
```python
# Source: tests/test_v3_tool_cli.py
exit_code = main(["describe", "rd_run_start"])
payload = json.loads(captured.out)

assert exit_code == 0
assert payload["name"] == "rd_run_start"
assert payload["category"] == "orchestration"
assert payload["recommended_entrypoint"] == "rd-agent"
assert payload["inputSchema"]["title"] == "RunStartRequest"
```

### Exact schema contract lock
```python
# Source: tests/test_phase13_v3_tools.py
tools = {tool["name"]: tool for tool in list_cli_tools()}

assert tools["rd_run_start"]["inputSchema"] == RunStartRequest.model_json_schema()
assert tools["rd_run_get"]["outputSchema"] == RunGetResult.model_json_schema()
assert tools["rd_memory_promote"]["outputSchema"] == MemoryGetResult.model_json_schema()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| schema-only tool catalog | schema plus `category` / `subcategory` / `recommended_entrypoint` | Phase 17, 2026-03-21 | operators can route at a coarse level, but still cannot see realistic request examples or post-success actions |
| ad hoc skill/reference guidance | repo-local `skills/rd-tool-catalog` aligned to the catalog categories | Phase 17, 2026-03-21 | routing philosophy exists, but tool entries still need machine-readable execution guidance |
| README CLI examples only | repo-local quick/full validation and list/describe examples in README | Phase 18, 2026-03-21 | public setup is clearer, but README is intentionally not the primary truth source for Phase 19 guidance |

**Deprecated/outdated:**
- Docs-only guidance as the source of truth for direct tools.
- Divergent payload contracts between `list` and `describe` without a strong
  need.
- Pulling Phase 20 stage-skill execution contracts into Phase 19 examples.

## Open Questions

1. **Should Phase 19 use one nested `guidance` object or several top-level guidance fields?**
   - What we know: `_catalog_entry()` is the one serializer, and stable
     machine-readable fields are required.
   - What's unclear: whether the project prefers a compact nested block or
     flatter JSON for operator ergonomics.
   - Recommendation: use one nested `guidance` object to reduce top-level field
     sprawl while leaving `category`, `subcategory`, and
     `recommended_entrypoint` untouched at top level.

2. **Does `describe` need a superset of `list`, or is one shared payload enough?**
   - What we know: both functions currently return the exact same shape.
   - What's unclear: whether planners want richer text on `describe`.
   - Recommendation: keep one shared payload for Phase 19 unless the plan can
     prove `list` would become too noisy; the current catalog already includes
     full schemas, so one concise example and short guidance block per tool is
     not the main payload cost.

3. **Does `skills/rd-tool-catalog/SKILL.md` need a narrow sync update in this phase?**
   - What we know: the skill already explains category-first routing and points
     to `rdagent-v3-tool list|describe`.
   - What's unclear: whether Phase 19 should explicitly mention the new
     guidance fields there or defer all narrative work to Phase 21.
   - Recommendation: only make a narrow alignment update if the skill would
     otherwise become inaccurate; do not broaden scope into README-style public
     narrative work.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest >=7.4.0` |
| Config file | `pyproject.toml` |
| Quick run command | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_catalog_guidance.py -q` |
| Full suite command | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py tests/test_phase19_tool_catalog_guidance.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUIDE-01 | every direct tool entry exposes at least one realistic common-path request example | unit/public-surface | `uv run python -m pytest tests/test_phase19_tool_catalog_guidance.py::test_every_tool_exposes_common_path_example -q` | `tests/test_phase19_tool_catalog_guidance.py` ❌ Wave 0 |
| GUIDE-02 | tool entries state when to use the direct tool, when not to use it, and which higher-level skill is preferred | unit/public-surface | `uv run python -m pytest tests/test_phase19_tool_catalog_guidance.py::test_tool_entries_expose_routing_guidance tests/test_v3_tool_cli.py -q` | `tests/test_v3_tool_cli.py` ✅ / `tests/test_phase19_tool_catalog_guidance.py` ❌ Wave 0 |
| GUIDE-03 | tool entries state the expected follow-up action after success, with strong coverage for orchestration and gating-sensitive tools | unit/public-surface + contract-alignment | `uv run python -m pytest tests/test_phase19_tool_catalog_guidance.py::test_tool_entries_expose_follow_up_guidance tests/test_phase13_v3_tools.py -q` | `tests/test_phase13_v3_tools.py` ✅ / `tests/test_phase19_tool_catalog_guidance.py` ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_catalog_guidance.py -q`
- **Per wave merge:** `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase16_tool_surface.py tests/test_phase19_tool_catalog_guidance.py -q`
- **Phase gate:** documented full suite green plus `uv run lint-imports`

### Wave 0 Gaps
- [ ] `tests/test_phase19_tool_catalog_guidance.py` — new Phase 19 requirement coverage for examples, routing guidance, and follow-up semantics
- [ ] `tests/test_v3_tool_cli.py` — extend `list` and `describe` assertions so the CLI surface proves the new guidance fields are actually emitted
- [ ] `tests/test_phase16_tool_surface.py` — extend full-registry assertions so all 23 tools must carry the required guidance contract, not just representative tools
- [ ] None for framework setup — existing `pytest` configuration and repo-local validation flow already exist

## Sources

### Primary (HIGH confidence)
- `.planning/phases/19-tool-catalog-operator-guidance/19-CONTEXT.md` - locked phase scope, decisions, and deferred boundaries
- `.planning/REQUIREMENTS.md` - `GUIDE-01` through `GUIDE-03`
- `.planning/STATE.md` - active milestone position and phase ordering
- `.planning/PROJECT.md` - current milestone goal and repository constraints
- `.planning/ROADMAP.md` - Phase 19 success criteria and boundary relative to Phases 20-21
- `v3/entry/tool_catalog.py` - `_ToolSpec`, `_catalog_entry()`, list/describe serialization, and direct-tool registry
- `v3/entry/tool_cli.py` - actual `rdagent-v3-tool list|describe` wrapper
- `v3/contracts/tool_io.py` - current request/response contracts and existing `recommended_next_step` fields
- `v3/contracts/recovery.py` and `v3/contracts/run.py` - recovery and run-state vocabulary relevant to follow-up semantics
- `v3/tools/orchestration_tools.py`, `v3/tools/recovery_tools.py`, `v3/tools/selection_tools.py`, `v3/tools/run_tools.py` - current success text and next-step signals
- `tests/test_v3_tool_cli.py` - CLI output assertions
- `tests/test_phase16_tool_surface.py` - full registry membership plus routing/schema coverage
- `tests/test_phase13_v3_tools.py` - exact schema equality and public-surface conformance
- `skills/rd-tool-catalog/SKILL.md` and `skills/rd-tool-catalog/references/tool-selection.md` - current routing guidance layer for direct tools
- `README.md` - current catalog narrative and documented quick/full verification commands

### Secondary (MEDIUM confidence)
- None. Repo-local sources were sufficient for this phase.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified directly from `pyproject.toml`, `README.md`, and the current repo entrypoints
- Architecture: HIGH - verified from `tool_catalog.py`, `tool_cli.py`, and existing test anchors
- Pitfalls: HIGH - derived from exact current assertions, shared serializer shape, and explicit phase boundaries

**Research date:** 2026-03-22
**Valid until:** 2026-04-21
