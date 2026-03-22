# Phase 21: Executable Public Surface Narrative - Research

**Researched:** 2026-03-22
**Domain:** Public README narrative and doc-surface regression locking for the standalone V3 skill/tool surface
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Deferred Ideas (OUT OF SCOPE)
- Any attempt to add new orchestration helpers, new CLI entrypoints, or new
  public transport abstractions belongs to a later phase.
- A machine-readable operator playbook generator belongs to later work under
  `SURFACE-03`, not this README-and-regression locking phase.
- Any broader restructuring of the product surface beyond the README and its
  regressions belongs to later roadmap work.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SURFACE-01 | Developer can read README and understand the standalone V3 surface as a multi-step skill-and-tool pipeline with concrete start, inspect, and continue paths. | README must be rewritten as one `Start -> Inspect -> Continue` playbook rooted in `rd-agent`, with inspect rules pointing to `SKILL.md` and `uv run rdagent-v3-tool describe ...`, and continue branches pointing to stage skills. |
| SURFACE-02 | Regression tests lock the new guidance fields and examples so the tool catalog and skill packages cannot drift back to schema-only descriptions. | Add a dedicated Phase 21 doc-surface regression file that reads `README.md` directly and cross-checks the README narrative against the Phase 19/20 public contract anchors and tool-inspection commands. |
</phase_requirements>

## Summary

Phase 21 is a documentation-integration phase, not a contract-design phase. The hard work of defining operator-usable tool metadata and stage-skill contracts already landed in Phases 19 and 20. The Phase 21 job is to make `README.md` an executable public narrative that routes a developer or agent through the existing surfaces without reading source code and without duplicating the full contract inventory that already lives in `skills/*/SKILL.md` and `rdagent-v3-tool describe`.

The current README is accurate but section-oriented. It introduces `rd-agent`, stage skills, `rd-tool-catalog`, and the routing model as separate reference blocks, but it does not yet read as a concrete path a caller can execute from start to inspect to continue. Current README regressions are similarly shallow: they mostly assert section presence and command strings, while the stronger operator guidance is currently locked in the Phase 19 and Phase 20 tests and in the tool/skill surfaces themselves.

The safest implementation strategy is to keep README narrow and agent-first: one mainline example for `Start -> Inspect -> Continue`, one representative continue branch, an explicit note that simpler work can use the single-branch minimum path, and outbound links to the real contract surfaces for exact fields. Pair that with a new dedicated Phase 21 regression file that locks the narrative semantics, while preserving the existing public-vs-internal boundary checks from Phase 18.

**Primary recommendation:** Recast `README.md` into an `rd-agent`-first `Start -> Inspect -> Continue` playbook and add a dedicated Phase 21 pytest file that asserts the narrative semantics, not just headings.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.11` | Runtime for repo scripts, CLI entrypoints, and tests | Project baseline from `pyproject.toml`; public commands already assume repo-local Python execution. |
| `pytest` | `9.0.2` | Doc-surface and contract regressions | Existing public-surface tests use direct file reads and explicit assertions; Phase 21 should extend that same style. |
| `README.md` | repo-local HEAD | Public narrative surface | This is the actual user-facing document Phase 21 must harden. |
| `skills/*/SKILL.md` | repo-local HEAD | Stable high-level skill contracts | Phase 20 already locked start/continue semantics here; README should summarize and link, not replace. |
| `rdagent-v3-tool` via `v3.entry.tool_cli` | repo-local HEAD | Public inspect/downshift surface | Phase 19 already locked examples, routing guidance, and follow-up semantics here. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | `2.12.5` | Source of stable public schema output for tool inspection | Only when README needs to cite the actual schema-backed inspect surface exposed by `rdagent-v3-tool describe`. |
| `import-linter` | `2.11` | Full-suite boundary verification | Keep in the phase gate because README/test work must not regress package boundaries indirectly. |
| `tests/test_phase17_surface_convergence.py` | repo-local HEAD | Existing README surface anchor | Keep or lightly update for baseline public-surface assertions. |
| `tests/test_phase18_planning_continuity.py` | repo-local HEAD | Public-vs-internal doc boundary anchor | Preserve the rule that README must not leak `.planning/STATE.md` continuity guidance. |
| `tests/test_phase19_tool_guidance.py` | repo-local HEAD | Tool metadata truth anchor | Use as proof that README inspect guidance points to a real, already-hardened surface. |
| `tests/test_phase20_rd_agent_skill_contract.py` and `tests/test_phase20_stage_skill_contracts.py` | repo-local HEAD | Skill contract truth anchors | Use as proof that README start/continue guidance stays aligned with existing skill docs. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| A new dedicated Phase 21 regression file | Only expand `tests/test_phase17_surface_convergence.py` | Possible, but it mixes terminology-era baseline checks with richer Phase 21 narrative semantics and makes future failures harder to localize. |
| README links out to skill/tool contracts for field truth | Duplicating full field inventories in README | Faster to read once, but drifts quickly and recreates the schema-catalog problem Phase 21 is supposed to avoid. |
| `rd-agent` as the main README entrypoint | `rd-tool-catalog` as a coequal top-level path | Violates locked routing hierarchy from Phases 17, 19, and 20. |

**Installation:**
```bash
uv sync --extra test
```

**Version verification:** Verified locally on 2026-03-22 from the repo environment and config: Python `>=3.11` in `pyproject.toml`; installed versions `pytest=9.0.2`, `pydantic=2.12.5`, `import-linter=2.11`.

## Architecture Patterns

### Recommended Project Structure
```text
README.md                                    # Public Start -> Inspect -> Continue playbook
skills/rd-agent/SKILL.md                     # Start-contract truth
skills/rd-propose/SKILL.md                   # Continue branch: framing -> build
skills/rd-code/SKILL.md                      # Continue branch: build -> verify
skills/rd-execute/SKILL.md                   # Continue branch: verify -> synthesize or blocked
skills/rd-evaluate/SKILL.md                  # Continue branch: synthesize -> continue/stop
skills/rd-tool-catalog/SKILL.md              # Inspect/downshift routing contract
v3/entry/tool_cli.py                         # `rdagent-v3-tool list/describe`
tests/test_phase21_public_surface_narrative.py
tests/test_phase17_surface_convergence.py
tests/test_phase18_planning_continuity.py
```

### Pattern 1: README As A Single Executable Mainline
**What:** Make the README read like one operator path, not a catalog of sections. The path should be `Start -> Inspect -> Continue`, with `rd-agent` first, inspect as a decision step, and stage skills as the continue branches.
**When to use:** For the main public README body.
**Example:**
```markdown
## Start -> Inspect -> Continue

### Start
Use `rd-agent` first. Start with the recommended multi-branch path, then note
that smaller tasks can use the strict minimum start contract from
`skills/rd-agent/SKILL.md`.

### Inspect
Inspect before continuing when the agent needs to confirm the current state,
the correct next surface, or the exact continuation contract.

- Read the relevant `skills/*/SKILL.md` file for the next high-level skill.
- If a lower-level direct tool is needed, run
  `uv run rdagent-v3-tool describe rd_run_start`.

### Continue
If the run is paused at one known stage, continue with the matching stage skill.
```
Source: repo-local constraints from `.planning/phases/21-executable-public-surface-narrative/21-CONTEXT.md`, `README.md`, and `skills/rd-agent/SKILL.md`.

### Pattern 2: Inspect Is A Decision Layer, Not A Reference Appendix
**What:** README must explicitly tell the agent to inspect current state and determine the next valid surface for the user, rather than making the user browse tools or contracts manually.
**When to use:** Any time the next step is not already obvious from the current paused stage.
**Example:**
```bash
uv run rdagent-v3-tool describe rd_run_start
```

```text
Continue the run with rd-agent using the returned run_id,
or inspect the returned branch_id and stage_key before handing off to a stage skill.
```
Source: `v3/entry/tool_catalog.py` live `rd_run_start` payload and `skills/rd-agent/SKILL.md`.

### Pattern 3: Dedicated Doc-Surface Regression Tests
**What:** Use focused pytest files that read `README.md` and assert exact guidance phrases and command strings. Do not use snapshots for public docs in this repo.
**When to use:** For every README narrative rule Phase 21 introduces.
**Example:**
```python
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"

def test_readme_contains_executable_mainline() -> None:
    text = README.read_text()
    assert "Start -> Inspect -> Continue" in text
    assert "Use `rd-agent` first" in text
    assert "uv run rdagent-v3-tool describe rd_run_start" in text
```
Source: `tests/test_phase17_surface_convergence.py` and `tests/test_phase18_planning_continuity.py`.

### Anti-Patterns to Avoid
- **README as a second schema catalog:** Do not copy the full field inventory from `skills/*/SKILL.md` or tool `inputSchema` blocks into the README.
- **Inspect buried in an appendix:** If inspect is not part of the main path, users still have to reverse-engineer the next step from separate sections.
- **`rd-tool-catalog` as a coequal top-level start path:** This breaks the locked `rd-agent`-first routing model.
- **Heading-only regressions:** Section presence alone will not catch drift in agent-first framing, inspect rules, or continue handoff semantics.
- **Leaking internal continuity into README:** Phase 18 already locked `.planning/STATE.md` out of the public README surface.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Public field truth in README | A second manual contract table duplicating every skill/tool field | Link to `skills/*/SKILL.md` and `uv run rdagent-v3-tool describe <tool>` | Phase 19/20 already hardened those surfaces; duplication guarantees drift. |
| README regression coverage | Snapshot/golden-file diffing for the whole README | Explicit pytest string assertions over targeted phrases and commands | This repo already uses focused assertions for public-surface stability. |
| Next-step routing explanation | New orchestration helpers or special README-only CLI aliases | Existing `rd-agent`, stage skills, and `rd-tool-catalog` surfaces | Phase 21 is constrained to narrative locking, not behavior expansion. |
| User-facing inspect workflow | Forcing users to manually browse catalog sections and deduce the next move | Agent-first inspect rule plus direct links to `SKILL.md` and `rdagent-v3-tool describe` | Phase 20 explicitly locked agent-led missing-field recovery and downshift behavior. |

**Key insight:** Phase 21 should assemble existing public truths into one path; it should not create a new truth source.

## Common Pitfalls

### Pitfall 1: Rewriting README as a richer catalog instead of a path
**What goes wrong:** The document gets longer and more detailed but still fails to tell a caller what to do first, when to inspect, and how to continue.
**Why it happens:** Existing README sections already exist, so it is tempting to polish them in place without changing the narrative shape.
**How to avoid:** Design around one mainline heading and one concrete example, then link out for details.
**Warning signs:** New prose adds more section detail but still lacks a visible `Start -> Inspect -> Continue` sequence.

### Pitfall 2: Duplicating Phase 20 field contracts in README
**What goes wrong:** README drifts away from the actual stage-skill contracts or tool metadata.
**Why it happens:** README feels user-facing, so writers often restate exact fields there.
**How to avoid:** Summarize minimum vs recommended path, then point to the exact `SKILL.md` contract for field-level truth.
**Warning signs:** README starts listing full continuation skeletons for all four stage skills.

### Pitfall 3: Treating inspect as optional or manual-user work
**What goes wrong:** The public surface still assumes the user must discover current state, the next stage skill, or the right direct tool on their own.
**Why it happens:** Inspect is easy to describe as a side note instead of a first-class step.
**How to avoid:** Explicitly state that the agent inspects current state, identifies the next valid step, and presents it to the user.
**Warning signs:** README wording says "browse the catalog" or "check the tools yourself" for normal continuation.

### Pitfall 4: Promoting `rd-tool-catalog` above its locked role
**What goes wrong:** README makes the direct-tool layer look like an equal starting path beside `rd-agent`.
**Why it happens:** Tool examples are concrete and easy to show.
**How to avoid:** Keep `rd-tool-catalog` inside the Inspect step as the downshift path after a high-level skill boundary is found insufficient.
**Warning signs:** `rd-tool-catalog` appears in top-level README flow before `rd-agent`.

### Pitfall 5: Testing headings instead of semantics
**What goes wrong:** README can regress back into catalog mode while tests still pass.
**Why it happens:** Existing Phase 17/18 tests already read README and assert headings, which is easy to extend but too weak for Phase 21.
**How to avoid:** Add tests for the mainline string, `rd-agent`-first framing, inspect rule, continue handoff, single-branch fallback note, and links to real skill/tool surfaces.
**Warning signs:** Tests only assert section names like `## CLI Tool Catalog` and `## Routing Model`.

## Code Examples

Verified patterns from repo-local public sources:

### README Inspect/Downshift Command
```bash
uv run rdagent-v3-tool describe rd_run_start
uv run rdagent-v3-tool describe rd_explore_round
```
Source: `README.md`

### Live Tool Follow-Up Semantics
```json
{
  "recommended_entrypoint": "rd-agent",
  "follow_up": {
    "next_entrypoint": "rd-agent",
    "next_action": "Continue the run with rd-agent using the returned run_id, or inspect the returned branch_id and stage_key before handing off to a stage skill."
  }
}
```
Source: `v3.entry.tool_catalog.get_cli_tool("rd_run_start")`

### Existing Doc-Surface Regression Style
```python
def test_readme_describes_skills_plus_cli_tools_surface():
    readme_text = README.read_text()
    assert "skills plus CLI tools" in readme_text
    assert "uv run rdagent-v3-tool describe rd_run_start" in readme_text
    assert "## Continue This Session" not in readme_text
```
Source: `tests/test_phase17_surface_convergence.py` and `tests/test_phase18_planning_continuity.py`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| README as section-by-section reference (`Default Orchestration`, `Stage Skills`, `CLI Tool Catalog`, `Routing Model`) | README as one executable `Start -> Inspect -> Continue` playbook that links to contracts | Phase 21 target on top of Phase 19/20 hardening, 2026-03-22 | Public surface becomes runnable from docs instead of merely readable. |
| Tool and skill guidance locked separately | README narrative cross-checks and stitches those locked surfaces together | Phase 19 and Phase 20 completed on 2026-03-22 | README can become concise without inventing new contract truth. |
| Heading-presence README tests | Narrative-semantic README tests | Phase 21 target | Regressions catch drift in operator flow, not only document outline. |

**Deprecated/outdated:**
- Schema-only README narration: replaced by a path-first public playbook.
- Manual-user tool discovery for common flows: replaced by agent-led inspect and routing.
- Treating `rd-tool-catalog` as a default entrypoint: replaced by inspect/downshift framing under `rd-agent`.

## Open Questions

1. **Should Phase 21 create a dedicated README flow section or reshape several adjacent sections?**
   - What we know: Context explicitly allows either, as long as the flow reads clearly as `Start -> Inspect -> Continue`.
   - What's unclear: Which option causes the least churn in existing Phase 17 README assertions.
   - Recommendation: Prefer one dedicated flow section near the top, then keep the existing detailed sections below it or collapse them into supporting subsections.

2. **Should existing Phase 17 tests be expanded heavily or should Phase 21 add a new focused regression file?**
   - What we know: The repo pattern for later phases is dedicated, phase-specific regression files such as `tests/test_phase19_tool_guidance.py` and `tests/test_phase20_stage_skill_contracts.py`.
   - What's unclear: Whether the planner wants minimal file count or better failure locality.
   - Recommendation: Add `tests/test_phase21_public_surface_narrative.py` and keep Phase 17/18 files for baseline invariants and public/internal boundary checks.

3. **What exact example payload should README use for the mainline example?**
   - What we know: Context locks the recommended multi-branch path first, with an immediate note that simple tasks can use the minimum contract.
   - What's unclear: Which scenario label and task summary best match the current milestone language.
   - Recommendation: Reuse existing Phase 20/19 terminology and literal fields so the example stays visibly grounded in live contracts.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` |
| Config file | `pyproject.toml` |
| Quick run command | `uv run python -m pytest tests/test_phase21_public_surface_narrative.py tests/test_phase17_surface_convergence.py tests/test_phase18_planning_continuity.py -q` |
| Full suite command | `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py tests/test_phase19_tool_guidance.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_phase21_public_surface_narrative.py -q && uv run lint-imports` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SURFACE-01 | README presents one concrete `Start -> Inspect -> Continue` path with `rd-agent` first, inspect rule, and continue handoff to stage skills | unit/doc-surface | `uv run python -m pytest tests/test_phase21_public_surface_narrative.py -q` | ❌ Wave 0 |
| SURFACE-02 | README regressions lock the narrative against drift from skill/tool guidance and preserve links to real surfaces | unit/doc-surface integration | `uv run python -m pytest tests/test_phase21_public_surface_narrative.py tests/test_phase17_surface_convergence.py tests/test_phase18_planning_continuity.py tests/test_phase19_tool_guidance.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_v3_tool_cli.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_phase21_public_surface_narrative.py -q`
- **Per wave merge:** `uv run python -m pytest tests/test_phase21_public_surface_narrative.py tests/test_phase17_surface_convergence.py tests/test_phase18_planning_continuity.py tests/test_phase19_tool_guidance.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_v3_tool_cli.py -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_phase21_public_surface_narrative.py` — covers SURFACE-01 and SURFACE-02 narrative semantics
- [ ] README quick/full verification commands likely need to include the new Phase 21 regression file once implemented
- [ ] If README headings are substantially reorganized, update `tests/test_phase17_surface_convergence.py` only for retained baseline public-surface invariants, not for Phase 21-specific narrative semantics

## Sources

### Primary (HIGH confidence)
- `.planning/phases/21-executable-public-surface-narrative/21-CONTEXT.md` - locked Phase 21 decisions, canonical refs, and deferred scope
- `.planning/REQUIREMENTS.md` - `SURFACE-01` and `SURFACE-02`
- `.planning/ROADMAP.md` - Phase 21 goal and success criteria
- `.planning/PROJECT.md` - milestone goal and product-surface constraints
- `.planning/STATE.md` - sequencing note that README/test locking follows Phase 19/20 hardening
- `README.md` - current public narrative shape and current quick/full verification commands
- `tests/test_phase17_surface_convergence.py` - current README section-presence regression style
- `tests/test_phase18_planning_continuity.py` - public-vs-internal documentation boundary tests
- `tests/test_phase19_tool_guidance.py` - current direct-tool guidance assertions
- `tests/test_phase20_rd_agent_skill_contract.py` - `rd-agent` contract truth anchor
- `tests/test_phase20_stage_skill_contracts.py` - stage-skill continuation truth anchor
- `skills/rd-agent/SKILL.md` - minimum start path, recommended multi-branch path, and inspect/escalation behavior
- `skills/rd-propose/SKILL.md`, `skills/rd-code/SKILL.md`, `skills/rd-execute/SKILL.md`, `skills/rd-evaluate/SKILL.md` - continue branch contracts
- `skills/rd-tool-catalog/SKILL.md` - downshift routing contract
- `v3/entry/tool_cli.py` and `v3/entry/tool_catalog.py` - live public inspect surface and tool follow-up semantics
- `pyproject.toml` - test framework and version constraints

### Secondary (MEDIUM confidence)
- None. Repo-local sources were sufficient.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - fully derived from repo-local config and installed environment
- Architecture: HIGH - driven by locked Phase 21 decisions plus current README/test patterns
- Pitfalls: HIGH - directly evidenced by current README shape and existing regression gaps

**Research date:** 2026-03-22
**Valid until:** 2026-03-29
