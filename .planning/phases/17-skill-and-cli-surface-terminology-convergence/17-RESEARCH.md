# Phase 17: Skill and CLI Surface Terminology Convergence - Research

**Researched:** 2026-03-21
**Domain:** standalone V3 public-surface consolidation
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Deferred Ideas (OUT OF SCOPE)
- Whether the standalone repo should eventually ship skill installation or skill
  discovery/runtime support beyond repo-local package structure belongs to a
  later phase.
- Any broader packaging or autonomy work beyond the Phase 17 surface layer
  belongs in Phase 18.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SURFACE-01 | Developer can discover the complete V3 CLI tool catalog through CLI-described commands rather than MCP-framed registry language. | Add machine-readable classification and routing fields in `v3/entry/tool_catalog.py`; surface them unchanged through `rdagent-v3-tool list|describe`; test for classification and anti-MCP wording. |
| SURFACE-02 | Developer can understand the public V3 surface as skills plus CLI tools consistently across README, ROADMAP, PROJECT, and tests. | Add real repo-local skill packages for the six public skills, rewrite README around skills-first routing, and add a doc-surface test that reads planning/docs text directly. |
| SURFACE-03 | Developer can distinguish high-level orchestration commands from direct primitive tools in the standalone V3 surface. | Encode `orchestration` / `inspection` / `primitives` plus stable primitive subcategories in catalog metadata; make `rd-tool-catalog` and README explain “stay high-level first, downshift only when needed.” |
</phase_requirements>

## Summary

Phase 17 is a surface-truth phase, not an orchestration phase. The only code seam that needs to move is the public metadata layer around the existing CLI catalog and skill entrypoints. `v3/entry/tool_catalog.py` already owns list/describe payload shape, and `v3/entry/tool_cli.py` is only a JSON passthrough. That makes classification work low-risk if it stays inside catalog metadata and tests.

The repo currently has entrypoint functions and a CLI script, but no real agent-facing skill packages. The clean implementation is to add repo-local `skills/.../SKILL.md` packages aligned to the existing `rd_*` entrypoint names, keep `rd-agent` as the default top-level path, and treat `rd-tool-catalog` as the selective downshift skill. README and tests should be rewritten around that model together, so the surface cannot drift again.

**Primary recommendation:** split Phase 17 into four slices: skill packages, catalog classification payloads, README/public narrative convergence, and surface-verification tests.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.11` | runtime | already fixed by the repo and sufficient for this phase |
| `pydantic` | `>=2,<3` | schema generation for list/describe payloads | current catalog/tests already depend on model JSON schema generation |
| `argparse` | stdlib | CLI parsing | current `rdagent-v3-tool` surface already uses it; no new CLI framework needed |
| Repo-local skill packages | repo-local | agent-facing public surface | Phase 17 needs truthful skill packaging, not a new installer/runtime |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=7.4.0` | public-surface regression tests | for catalog payload, README, and requirement-convergence assertions |
| `import-linter` | `>=2.3,<3.0` | boundary gate | keep Phase 17 from leaking into lower-level orchestration/runtime layers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| repo-local `skills/.../SKILL.md` packages | skill install/discovery runtime | out of scope for Phase 17; belongs to Phase 18 |
| stable catalog metadata | prose-only guidance in descriptions | forces skills/tests to parse English and will drift again |

**Installation:**
```bash
uv sync --extra test
```

## Architecture Patterns

### Recommended Project Structure
```text
skills/
├── rd-agent/
│   └── SKILL.md
├── rd-propose/
│   └── SKILL.md
├── rd-code/
│   └── SKILL.md
├── rd-execute/
│   └── SKILL.md
├── rd-evaluate/
│   └── SKILL.md
└── rd-tool-catalog/
    └── SKILL.md
```

### Pattern 1: Catalog-Metadata Ownership
**What:** add all stable routing/classification fields in `_ToolSpec` and `_catalog_entry`, not in CLI code and not in tests.
**When to use:** for top-level category, primitive subcategory, and “prefer high-level skill first” guidance.
**Implementation seam:** [`v3/entry/tool_catalog.py`](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py)

### Pattern 2: CLI as Pure Transport
**What:** keep `v3/entry/tool_cli.py` as a thin `list` / `describe` JSON passthrough.
**When to use:** always; this phase should not add runtime behavior beyond surfacing new catalog fields.
**Implementation seam:** [`v3/entry/tool_cli.py`](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_cli.py)

### Pattern 3: Skills Mirror Entrypoints
**What:** one repo-local skill package per public entrypoint, with names aligned to `rd_agent`, `rd_propose`, `rd_code`, `rd_execute`, `rd_evaluate`, plus `rd-tool-catalog`.
**When to use:** for agent invocation and routing guidance, not as a new execution runtime.
**Implementation seam:** new `skills/.../SKILL.md` tree; skill structure/details delegated to `$skill-architect`.

### Likely Plan Slices
1. Create the six public skill packages via `$skill-architect`.
2. Extend catalog metadata and CLI outputs with stable classification fields.
3. Rewrite README around `rd-agent` first, staged skills next, `rd-tool-catalog` as downshift.
4. Retarget and add tests so docs/tests assert the same public model.

### Anti-Patterns to Avoid
- **Classification in prose only:** tests and skills will infer categories from descriptions and drift.
- **Runtime/discovery work in Phase 17:** skill install/discovery infrastructure is explicitly deferred.
- **Touching orchestration services:** `rd_agent` semantics and lower layers are not part of this phase.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| tool classification lookup | ad hoc parsing in README/tests/skills | stable fields emitted by `list_cli_tools()` | one source of truth prevents drift |
| skill execution runtime | installer/discovery mechanism | repo-local skill packages only | runtime support is out of scope |
| CLI behavior branching | custom logic in `tool_cli.py` | metadata-only extension in `tool_catalog.py` | preserves the existing thin CLI contract |

**Key insight:** Phase 17 succeeds by centralizing surface truth, not by adding new behavior.

## Common Pitfalls

### Pitfall 1: Updating docs without updating payloads
**What goes wrong:** README says “skills plus CLI tools” but `rdagent-v3-tool list` still exposes only generic `surface=cli_tool`.
**How to avoid:** make tests assert new classification fields directly from CLI JSON.

### Pitfall 2: Adding skills as placeholders
**What goes wrong:** directories exist, but they do not state when to use the skill, when to route to `rd-tool-catalog`, and when not to use it.
**How to avoid:** make those three boundaries part of every skill package acceptance check.

### Pitfall 3: Smuggling lower-level changes into a surface phase
**What goes wrong:** catalog work expands into orchestration/runtime refactors.
**How to avoid:** restrict edits to skill packages, catalog metadata, CLI output, README, and tests.

## Code Examples

### Catalog payload shape should own classification
```python
# Source: v3/entry/tool_catalog.py
return {
    "name": spec.name,
    "surface": "cli_tool",
    "category": "orchestration" | "inspection" | "primitives",
    "subcategory": "branch" | "memory" | "artifacts" | None,
    "recommended_entrypoint": "rd-agent" | "rd-tool-catalog",
    "command": f"rdagent-v3-tool describe {spec.name}",
    "inputSchema": ...,
    "outputSchema": ...,
}
```

### Skill package boundary contract
```markdown
# Source: skills/<skill>/SKILL.md
- When to use this skill
- When to route to `rd-tool-catalog`
- When not to use this skill
```

## Open Questions

1. **Should a thin routing skill exist in addition to the six locked skills?**
   - What we know: the context leaves this to `$skill-architect`.
   - Recommendation: treat it as optional and non-blocking; do not let it delay the six required skills.

2. **Should `v3.entry.__all__` export `rd_agent` for namespace symmetry?**
   - What we know: stage entrypoints are exported today, `rd_agent` is not.
   - Recommendation: decide during implementation only if the public namespace is being used as a documented surface; otherwise leave it untouched to keep scope tight.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest >=7.4.0` |
| Config file | `pyproject.toml` |
| Quick run command | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q` |
| Full suite command | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SURFACE-01 | `rdagent-v3-tool list|describe` exposes stable classification and non-MCP wording | unit/public-surface | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase17_surface_convergence.py -q` | `tests/test_v3_tool_cli.py` ✅ / `tests/test_phase17_surface_convergence.py` ❌ Wave 0 |
| SURFACE-02 | README, PROJECT, ROADMAP, REQUIREMENTS, and tests all describe skills + CLI tools consistently | doc-surface regression | `uv run python -m pytest tests/test_phase17_surface_convergence.py -q` | ❌ Wave 0 |
| SURFACE-03 | high-level orchestration vs primitives is explicit in catalog metadata and guidance | unit/public-surface | `uv run python -m pytest tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q` | `tests/test_phase16_tool_surface.py` ✅ / `tests/test_phase17_surface_convergence.py` ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q`
- **Per wave merge:** `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q`
- **Phase gate:** full suite green plus `uv run lint-imports`

### Wave 0 Gaps
- [ ] `tests/test_phase17_surface_convergence.py` — covers SURFACE-01, SURFACE-02, and SURFACE-03 end-to-end at the public-surface level

## Sources

### Primary (HIGH confidence)
- [`17-CONTEXT.md`](/Users/michael-liang/Code/my-RDagent-V3/.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-CONTEXT.md) - locked decisions, phase boundary, skill set, classification rules
- [`PROJECT.md`](/Users/michael-liang/Code/my-RDagent-V3/.planning/PROJECT.md) - milestone goal and constraints
- [`ROADMAP.md`](/Users/michael-liang/Code/my-RDagent-V3/.planning/ROADMAP.md) - phase success criteria
- [`REQUIREMENTS.md`](/Users/michael-liang/Code/my-RDagent-V3/.planning/REQUIREMENTS.md) - SURFACE-01/02/03 definitions
- [`v3/entry/tool_catalog.py`](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py) - current metadata ownership seam
- [`v3/entry/tool_cli.py`](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_cli.py) - CLI passthrough seam
- [`README.md`](/Users/michael-liang/Code/my-RDagent-V3/README.md) - current public narrative
- [`tests/test_v3_tool_cli.py`](/Users/michael-liang/Code/my-RDagent-V3/tests/test_v3_tool_cli.py) - current CLI payload assertions
- [`tests/test_phase16_tool_surface.py`](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase16_tool_surface.py) - current tool-surface coverage
- [`pyproject.toml`](/Users/michael-liang/Code/my-RDagent-V3/pyproject.toml) - test stack and CLI entrypoint

### Secondary (MEDIUM confidence)
- [`17-EXTERNAL-REFERENCES.md`](/Users/michael-liang/Code/my-RDagent-V3/.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-EXTERNAL-REFERENCES.md) - local summary of external skill/tool-use inspirations
- [`/Users/michael-liang/.agents/skills/skill-architect/SKILL.md`](/Users/michael-liang/.agents/skills/skill-architect/SKILL.md) - skill package design constraints

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - uses the existing repo stack from `pyproject.toml`; no new runtime dependencies required
- Architecture: MEDIUM - catalog and CLI seams are clear, but exact skill folder internals are delegated to `$skill-architect`
- Pitfalls: HIGH - directly derived from current code/test coupling and locked phase boundary

**Research date:** 2026-03-21
**Valid until:** 2026-04-20
