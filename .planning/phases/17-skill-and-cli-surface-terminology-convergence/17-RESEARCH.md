# Phase 17: Skill and CLI Surface Terminology Convergence - Research

**Researched:** 2026-03-21
**Domain:** standalone V3 public surface, skill packaging, CLI catalog classification, README/test convergence
**Confidence:** HIGH

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
| SURFACE-01 | Developer can discover the complete V3 CLI tool catalog through CLI-described commands rather than MCP-framed registry language. | Keep `rdagent-v3-tool list/describe` as the discovery path, enrich catalog metadata in `v3/entry/tool_catalog.py`, and update CLI tests to assert structured classification and routing metadata. |
| SURFACE-02 | Developer can understand the public V3 surface as skills plus CLI tools consistently across README, ROADMAP, PROJECT, and tests. | Create real `skills/.../SKILL.md` packages, make README use the same public names/order/routing model as the planning docs, and add tests that assert skill-package and README alignment. |
| SURFACE-03 | Developer can distinguish high-level orchestration commands from direct primitive tools in the standalone V3 surface. | Add stable top-level category fields plus primitive subcategories in the catalog, describe the high-level-to-primitive routing rule in skills/README, and add classification-aware surface tests. |
</phase_requirements>

## Summary

The current implementation already has the correct technical center of gravity for this phase: `rd_agent` is the top orchestration entrypoint, stage-specific entrypoints already exist, and `rdagent-v3-tool` exposes a flat schema-described catalog backed by `v3/entry/tool_catalog.py`. The phase is not blocked by missing orchestration capabilities. It is blocked by surface honesty: there are no real skill packages yet, the CLI catalog exposes no machine-readable classification beyond `"surface": "cli_tool"`, the README still presents Python module names rather than the desired public skill names, and the tests only verify flat catalog membership/schema rather than the intended skill-plus-CLI routing model.

The planning documents are already ahead of the code/docs surface. `PROJECT.md`, `ROADMAP.md`, `REQUIREMENTS.md`, and `17-CONTEXT.md` consistently describe the product as skills plus CLI tools, but the repo root still has no `skills/` tree, README still uses `rd_agent`-style module naming, and `tests/test_v3_tool_cli.py` plus `tests/test_phase16_tool_surface.py` assert the old minimal catalog contract. Phase 17 should therefore be planned as a surface-convergence phase, not a refactor of V3 contracts or handlers.

**Primary recommendation:** keep all existing tool handlers and orchestration semantics intact; implement Phase 17 by adding real `skills/` packages, making `tool_catalog.py` the single source of structured classification truth, rewriting README around the locked routing model, and retargeting tests from flat existence checks to public-surface assertions.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.11` declared, `3.12.12` verified in `.venv` | runtime, stdlib `argparse`, JSON output, file layout | Existing code already depends on `enum.StrEnum`, so Phase 17 should stay inside the current Python baseline rather than introducing compatibility shims. |
| `pydantic` | `>=2,<3` declared, `2.12.5` verified | request/response schemas and catalog schema emission | The catalog already derives JSON schema directly from Pydantic contracts; this is the correct source of truth for public CLI schemas. |
| repo-local `skills/.../SKILL.md` packages | new in Phase 17 | agent-facing public skill surface | Locked decision: real skill packages must exist; do not fake this with README-only naming. |
| `argparse` via `v3.entry.tool_cli` | stdlib | stable `rdagent-v3-tool list/describe` CLI surface | Existing CLI is already transport-free and script-backed through `pyproject.toml`; no framework migration is needed for this phase. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=7.4.0` declared, `9.0.2` verified | surface-regression tests | Use for CLI payload, README alignment, skill-package existence, and category/routing assertions. |
| `import-linter` | `>=2.3,<3.0` declared, `2.11` verified | import boundary protection | Keep using it to prove Phase 17 did not pull surface work into legacy or lower-level runtime ownership. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| extending `tool_catalog.py` metadata | separate catalog registry file or test-side name inference | Bad fit. Duplicates source of truth and guarantees doc/test drift. |
| keeping `argparse` | Typer/Click rewrite | Unnecessary for this phase. Adds surface churn without helping the locked requirements. |
| README-only “skills” wording | real `skills/.../SKILL.md` packages | Rejected by locked decisions. README-only renaming would keep the surface dishonest. |

**Installation:**
```bash
uv sync --extra test
```

**Version verification:** verified locally in the project venv on 2026-03-21.
```bash
./.venv/bin/python -c "import sys, json, pydantic, pytest; import importlinter; print(json.dumps({'python': sys.version.split()[0], 'pydantic': pydantic.__version__, 'pytest': pytest.__version__, 'import_linter': importlinter.__version__}))"
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

v3/
└── entry/
    ├── rd_agent.py
    ├── rd_propose.py
    ├── rd_code.py
    ├── rd_execute.py
    ├── rd_evaluate.py
    ├── tool_catalog.py
    └── tool_cli.py
```

### Pattern 1: Keep Python Entry Modules as the Implementation Anchors
**What:** The public skill packages should point to existing `v3.entry.*` implementation modules instead of introducing a second execution layer.
**When to use:** For every Phase 17 skill package.
**Example:**
```python
# Source: v3/entry/rd_agent.py
start_response = call_cli_tool(
    "rd_run_start",
    {
        "title": title,
        "task_summary": task_summary,
        "scenario_label": scenario_label,
        "initial_branch_label": initial_branch_label,
        "execution_mode": execution_mode,
        "max_stage_iterations": max_stage_iterations,
    },
    service=run_service,
)
```

### Pattern 2: Make Catalog Classification a Single Source of Truth
**What:** Extend `_ToolSpec` and `_catalog_entry()` so category data, primitive subcategory data, and routing hints are emitted by the catalog itself.
**When to use:** For all CLI discovery output consumed by skills, tests, and docs.
**Example:**
```python
# Source pattern to extend: v3/entry/tool_catalog.py
@dataclass(frozen=True)
class _ToolSpec:
    name: str
    title: str
    description: str
    handler: Callable[..., dict[str, Any]]
    request_model: type[BaseModel]
    response_model: type[BaseModel]
    dependency_names: tuple[str, ...]
    # Phase 17 should add classification fields here rather than infer them elsewhere.


def _catalog_entry(spec: _ToolSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "title": spec.title,
        "description": spec.description,
        "surface": "cli_tool",
        "command": f"rdagent-v3-tool describe {spec.name}",
        "inputSchema": spec.request_model.model_json_schema(),
        "outputSchema": spec.response_model.model_json_schema(),
    }
```

### Pattern 3: High-Level Skills First, Catalog Second, Primitive Tools Last
**What:** The public routing model should always start with `rd-agent` or a stage skill, then fall back to `rd-tool-catalog`, then downshift to primitives only when the higher-level boundary is insufficient.
**When to use:** README narrative, every `SKILL.md`, and catalog guidance fields.
**Example:**
```text
1. Use rd-agent for normal orchestration.
2. If a stage-specific action is needed, route to rd-propose / rd-code / rd-execute / rd-evaluate.
3. If a direct tool is required, query rd-tool-catalog.
4. Only then choose a primitive tool by category and primitive subcategory.
```

### Recommended Category Mapping
**What:** A concrete category map inferred from current tool responsibilities plus locked phase constraints.
**When to use:** As the default implementation unless `skill-architect` finds a better mapping that still preserves the locked top-level taxonomy.

| Tool | Top-level category | Primitive subcategory | Confidence |
|------|--------------------|-----------------------|------------|
| `rd_run_start` | `orchestration` | `null` | HIGH |
| `rd_explore_round` | `orchestration` | `null` | HIGH |
| `rd_converge_round` | `orchestration` | `null` | HIGH |
| `rd_run_get`, `rd_branch_board_get`, `rd_branch_get`, `rd_branch_list`, `rd_stage_get`, `rd_artifact_list`, `rd_recovery_assess`, `rd_memory_get`, `rd_memory_list`, `rd_branch_paths_get` | `inspection` | `null` | HIGH |
| `rd_branch_fork`, `rd_branch_prune` | `primitives` | `branch_lifecycle` | MEDIUM |
| `rd_branch_share_assess`, `rd_branch_share_apply` | `primitives` | `branch_sharing` | MEDIUM |
| `rd_branch_shortlist`, `rd_branch_merge`, `rd_branch_fallback`, `rd_branch_select_next` | `primitives` | `convergence` | MEDIUM |
| `rd_memory_create`, `rd_memory_promote` | `primitives` | `memory` | MEDIUM |

**Inference note:** the top-level categories are locked by context; the primitive subcategories above are a planning recommendation, not current code truth.

### Anti-Patterns to Avoid
- **Doc-only renaming:** saying “skills” in README without creating real skill packages fails the locked surface-realization requirement.
- **Classification by regex or prose:** if tests or skills infer categories from tool names/descriptions, drift is guaranteed.
- **Changing handler contracts to fit docs:** Phase 17 is a surface layer phase; do not rewrite `v3/contracts/tool_io.py` or tool handler semantics unless a surface-only export issue truly requires it.
- **Reducing current CLI payloads:** `list` and `describe` already work and are tested; add fields, do not replace or remove existing ones.
- **Treating archived Phase 16 artifacts as the main surface docs:** historical verification can stay historical; update current public surfaces first.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| tool classification | ad hoc category inference in tests/README | structured fields emitted by `v3/entry/tool_catalog.py` | One source of truth avoids inconsistent routing and stale docs. |
| skill surface | prose-only mention of skills | real `skills/.../SKILL.md` packages created via `$skill-architect` | Locked decision and truthful public surface. |
| new orchestration shim | wrapper runtime around `v3.entry` functions | existing `v3.entry.rd_*` modules | Prevents semantic drift and scope creep. |
| new CLI framework | Typer/Click migration | existing `v3.entry.tool_cli` + `argparse` | No requirement benefit; high churn. |
| test-only surface model | assertions that inspect names without routing meaning | classification-aware tests plus README/skill existence assertions | SURFACE-02 and SURFACE-03 need semantic coverage, not just membership smoke checks. |

**Key insight:** this phase should centralize public-surface meaning, not create parallel metadata systems.

## Common Pitfalls

### Pitfall 1: Public skill names drift from Python module names
**What goes wrong:** Docs and skill packages use hyphenated public names while code/tests still refer to underscore module names inconsistently.
**Why it happens:** Current code is Python-first (`rd_agent.py`, `rd_propose.py`), while the locked public surface is skill-first (`rd-agent`, `rd-propose`).
**How to avoid:** Define one explicit mapping table in README and/or skill metadata. Keep code module names unchanged unless there is a strong reason to rename Python files.
**Warning signs:** README mixes `rd_agent` and `rd-agent` in operator-facing sections; tests assert one style while skills use another.

### Pitfall 2: Category truth lives in multiple places
**What goes wrong:** README, skills, and tests each hardcode different tool categories or primitive groups.
**Why it happens:** The current catalog output has only `"surface": "cli_tool"`, so downstream code is forced to infer meaning.
**How to avoid:** Put classification fields in `_ToolSpec` and assert them from CLI tests.
**Warning signs:** category names appear only in prose or only in tests.

### Pitfall 3: Surface phase quietly mutates orchestration semantics
**What goes wrong:** A terminology cleanup starts touching `v3/tools`, `v3/orchestration`, or `v3/contracts` behavior.
**Why it happens:** The catalog touches many domains and can tempt “cleanup while here” refactors.
**How to avoid:** Restrict Phase 17 changes to `skills/`, `README.md`, `v3/entry/tool_catalog.py`, `v3/entry/tool_cli.py`, `v3/entry/__init__.py`, and surface-oriented tests unless a concrete blocker appears.
**Warning signs:** planned tasks mention service logic, contract enums, or handler return shapes unrelated to metadata.

### Pitfall 4: Validation runs under the wrong interpreter
**What goes wrong:** bare `python` uses a local 3.9 interpreter and fails on `enum.StrEnum`, producing misleading errors.
**Why it happens:** The repo declares `>=3.11`, but shell-default Python can still be older.
**How to avoid:** use `uv sync --extra test` first, then run `./.venv/bin/python` or `uv run`.
**Warning signs:** `ImportError: cannot import name 'StrEnum' from 'enum'`.

### Pitfall 5: Historical artifacts get treated as current product truth
**What goes wrong:** developers try to make archived Phase 16 verification prose perfectly match the new Phase 17 surface and end up rewriting history.
**Why it happens:** `16-VERIFICATION.md` and `V3-EXTRACTION-HANDOFF.md` still contain old framing notes.
**How to avoid:** prioritize current public surfaces first; only touch historical artifacts if the phase explicitly needs active internal references cleaned up.
**Warning signs:** plan tasks spend more effort rewriting archived docs than creating actual skill packages or classification metadata.

## Code Examples

Verified patterns from repo sources:

### Catalog entry generation is already centralized
```python
# Source: v3/entry/tool_catalog.py
def _catalog_entry(spec: _ToolSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "title": spec.title,
        "description": spec.description,
        "surface": "cli_tool",
        "command": f"rdagent-v3-tool describe {spec.name}",
        "inputSchema": spec.request_model.model_json_schema(),
        "outputSchema": spec.response_model.model_json_schema(),
    }
```

### CLI discovery surface is small and stable
```python
# Source: v3/entry/tool_cli.py
subparsers.add_parser("list", help="List the available V3 CLI tools")

describe_parser = subparsers.add_parser("describe", help="Describe one V3 CLI tool")
describe_parser.add_argument("name", help="Tool name, for example rd_run_start")
```

### `rd_agent` already anchors the high-level route
```python
# Source: v3/entry/rd_agent.py
if branch_hypotheses and len(branch_hypotheses) > 1:
    explore_round = multi_branch_service.run_exploration_round(...)
    converge_round = multi_branch_service.run_convergence_round(...)
    return {
        "structuredContent": {
            "run": run_snapshot.model_dump(mode="json"),
            "board": converge_round.board.model_dump(mode="json"),
            "mode": converge_round.board.mode.value,
            "recommended_next_step": converge_round.recommended_next_step,
            "selected_branch_id": converge_round.selected_branch_id,
            "dispatches": explore_round.dispatched_branch_ids,
            "merge_summary": converge_round.merge_summary,
        },
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| in-process MCP-shaped compatibility surface | transport-free CLI catalog in `v3/entry/tool_catalog.py` plus `rdagent-v3-tool` | v1.0 extraction on 2026-03-21 | Phase 17 should finish terminology and packaging convergence, not reintroduce transport abstractions. |
| planning docs tied to `MCP-02` | standalone `SURFACE-01` / `SURFACE-02` / `SURFACE-03` requirement family | 2026-03-21 standalone milestone kickoff | Current planning docs are already aligned; implementation/docs/tests must catch up. |
| module-oriented mention of “skill entrypoints” | locked target is real skill packages plus CLI tools | Phase 17 target | This is the main remaining public-surface honesty gap. |

**Deprecated/outdated:**
- `MCP-02` as an active standalone-repo public-surface label: replaced by `SURFACE-*`.
- `v3/entry/mcp_tools.py` as current surface truth: historical only; current repo uses `tool_catalog.py`.

## Open Questions

1. **Where should the new skill packages live?**
   - What we know: the repo currently has no `skills/` tree, and locked context delegates exact layout to `$skill-architect`.
   - What's unclear: whether the repo should use a simple top-level `skills/` directory or a deeper package layout.
   - Recommendation: plan the phase assuming a top-level `skills/` root, but keep the exact layout as a `skill-architect` decision task.

2. **Should a thin routing skill exist in addition to the locked core set?**
   - What we know: the context allows `skill-architect` to decide this.
   - What's unclear: whether `rd-tool-catalog` alone is sufficient as the downshift/routing surface.
   - Recommendation: make this an explicit design decision inside the skill-creation plan, not an implicit assumption.

3. **Should `rd_agent` be exported from `v3.entry.__all__`?**
   - What we know: `README.md` and roadmap treat it as the primary public entrypoint, but `v3/entry/__init__.py` currently exports only the stage skills plus catalog helpers.
   - What's unclear: whether this omission is intentional or just lagging surface truth.
   - Recommendation: treat this as a Phase 17 surface-alignment check; fixing the export is low-risk if the public namespace intends to be complete.

4. **Should archived internal docs be updated?**
   - What we know: `16-VERIFICATION.md` and `V3-EXTRACTION-HANDOFF.md` still preserve some legacy wording.
   - What's unclear: whether this phase wants only current public surface convergence or also active internal artifact cleanup.
   - Recommendation: default to leaving archived/history docs alone unless they are still referenced as active operator guidance.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` |
| Config file | `pyproject.toml` |
| Quick run command | `./.venv/bin/python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py -q` |
| Full suite command | `./.venv/bin/python -m pytest tests/test_v3_tool_cli.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SURFACE-01 | CLI `list` / `describe` expose the full catalog with stable classification fields and no MCP framing | unit / CLI | `./.venv/bin/python -m pytest tests/test_v3_tool_cli.py -q` | ✅ |
| SURFACE-02 | README, skill packages, and public names align around the same skill-plus-CLI model | unit / docs | `./.venv/bin/python -m pytest tests/test_phase17_surface_model.py -q` | ❌ Wave 0 |
| SURFACE-03 | High-level orchestration tools vs primitive tools are explicit and machine-readable | unit / catalog | `./.venv/bin/python -m pytest tests/test_phase16_tool_surface.py tests/test_phase17_surface_model.py -q` | `tests/test_phase16_tool_surface.py` ✅, `tests/test_phase17_surface_model.py` ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `./.venv/bin/python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py -q`
- **Per wave merge:** `./.venv/bin/python -m pytest tests/test_v3_tool_cli.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py -q`
- **Phase gate:** full focused suite green plus `./.venv/bin/lint-imports`

### Wave 0 Gaps
- [ ] `tests/test_phase17_surface_model.py` — covers skill package existence, README routing model, public skill naming, and classification-aware expectations for SURFACE-02 / SURFACE-03
- [ ] README assertions — decide which phrases/order should be locked in tests versus left to manual narrative review
- [ ] Skill-package file existence checks — add canonical expectations for the locked minimum skill set

## Sources

### Primary (HIGH confidence)
- Repo code: `v3/entry/tool_catalog.py` — current CLI catalog inventory, metadata shape, and dispatch seam
- Repo code: `v3/entry/tool_cli.py` — current `list` / `describe` surface and JSON output path
- Repo code: `v3/entry/rd_agent.py` — current high-level orchestration anchor
- Repo docs: `.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-CONTEXT.md` — locked scope, routing rules, and delivery boundaries
- Repo docs: `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` — already-aligned standalone public-surface language
- Repo tests: `tests/test_v3_tool_cli.py`, `tests/test_phase16_tool_surface.py`, `tests/test_phase13_v3_tools.py`, `tests/test_phase14_skill_agent.py` — current verification truth and gaps
- Repo config: `pyproject.toml`, `.planning/config.json` — runtime/test stack and validation enablement
- Fresh local validation on 2026-03-21:
  - `./.venv/bin/python -m pytest tests/test_v3_tool_cli.py tests/test_phase16_tool_surface.py -q` → 5 passed
  - `./.venv/bin/lint-imports` → 8 kept, 0 broken
  - `./.venv/bin/rdagent-v3-tool list`
  - `./.venv/bin/rdagent-v3-tool describe rd_explore_round`

### Secondary (MEDIUM confidence)
- Repo-local summary: `.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-EXTERNAL-REFERENCES.md` — design inspirations from GSD, Superpowers, and Anthropic advanced tool use

### Tertiary (LOW confidence)
- Primitive second-level category names in this document (`branch_lifecycle`, `branch_sharing`, `convergence`, `memory`) — planning recommendation inferred from current tool behavior; not yet verified by implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - derived from `pyproject.toml`, verified `.venv` package versions, and current CLI/test execution
- Architecture: HIGH - based on direct inspection of `v3.entry` modules and locked Phase 17 context
- Pitfalls: MEDIUM-HIGH - mostly confirmed from current repo state; interpreter/cache quirks are environment-sensitive but were reproduced locally

**Research date:** 2026-03-21
**Valid until:** 2026-04-20
