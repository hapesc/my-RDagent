# RDagent Skill Refactoring Blueprint v2

This blueprint supersedes v1 (260323-qj9). An executor can pick up any wave
and execute it without reading v1 or the original qfz analysis. Every
extraction target names the source skill file, the source sections, and the
destination file. Every test strategy names the pytest command and the exact
assertion behavior change.

---

## Part 0: Existing Infrastructure Inventory

Document what already works and **must not be rebuilt**.

### Installer: `_install_skill_support_files()`

Location: `v3/devtools/skill_install.py` line 247.

```python
def _install_skill_support_files(*, source_dir: Path, destination: Path, mode: str) -> None:
    for child in sorted(source_dir.iterdir()):
        if child.name == "SKILL.md":
            continue
        target = destination / child.name
        if mode == "link":
            target.symlink_to(child, target_is_directory=child.is_dir())
            continue
        if child.is_dir():
            shutil.copytree(child, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            continue
        shutil.copy2(child, target)
```

Behavior: iterates all children of a source skill dir **except** `SKILL.md`,
and symlinks (link mode) or copies (copy mode) each one to the installed
destination. This means adding `workflows/` or `references/` inside any
`skills/{name}/` directory will be **automatically installed** to
`.claude/skills/{name}/` and `.codex/skills/{name}/` with zero installer
changes.

### Installer: `_render_installed_skill()`

Location: `v3/devtools/skill_install.py` line 265.

Appends the "Installed runtime bundle" section with the concrete `bundle_root`
path. This already gives installed skills the correct execution root. Adding
internal workflow or reference load lines to SKILL.md will be faithfully
reproduced in the installed version.

### Installer: `_render_installed_skill()` resource resolution

Line 279: `Relative resources for this installed skill still resolve inside
{bundle_root / "skills" / source_dir.name}`.

This means `workflows/continue.md` and `references/failure-routing.md`
inside a skill directory will resolve correctly in the installed skill
because the bundle root already symlinks the entire `skills/` tree.

### Test: `test_phase18_skill_installation.py`

Already tests that non-SKILL.md files (like `notes.txt`) are
symlinked/copied during install. Subdirectories like `workflows/` will be
handled identically by `_install_skill_support_files()` because it iterates
all children except `SKILL.md`.

### Test: `test_phase20_stage_skill_contracts.py`

Tests specific text patterns in SKILL.md files:

- `"## Continue contract"` in all 4 stage skills
- `"## Required fields"` in all 4 stage skills
- `"## If information is missing"` in all 4 stage skills
- `` "`run_id`" ``, `` "`branch_id`" ``, `` "`summary`" ``, `` "`artifact_ids`" `` in all 4
- `` "`blocking_reasons`" `` in rd-execute
- `` "`recommendation`" ``, `` "`continue`" ``, `` "`stop`" `` in rd-evaluate
- `"inspect current run or branch state"` in all 4
- `"surface the exact missing values"` in all 4
- `"continue a paused run"` in all 4
- `"the next high-level action is `rd-code`"` in rd-propose (etc.)

**These tests are the regression gate.** Any extraction that removes these
strings from SKILL.md **must also update these tests**.

### Test: `test_phase20_rd_agent_skill_contract.py`

Tests rd-agent SKILL.md patterns: minimum start contract fields, separated
minimum vs recommended paths, default stop behavior, tool-catalog-as-
escalation, agent-led missing-field recovery, success contract.

### Test: `test_phase14_stage_skills.py` and `test_phase14_skill_agent.py`

Additional regression tests that should continue to pass throughout the
refactoring.

### Conclusion

The installer already handles support files. The blueprint does **NOT**
propose new symlink infrastructure, new installer features, or a `_shared`
directory as Wave 0. The per-skill `workflows/` and `references/`
directories are the natural extension of the existing mechanism.

---

## Part 1: Target Architecture

After refactoring, each skill follows this directory structure:

```
skills/{skill-name}/
  SKILL.md              # thin adapter: trigger, boundary, execution context, output contract
  workflows/            # internal step-by-step pipeline (conditional load only)
    continue.md         # stage continuation pipeline (EACH stage owns its own)
  references/           # long rules, checklists (conditional load only)
```

### Key differences from v1

1. **NO `skills/_shared/` directory in Wave 0.** Shared references MAY be
   introduced in a later wave AFTER proving the per-skill workflow pattern
   works in installed runtimes.

2. **Each stage skill gets its own `workflows/continue.md`** that owns the
   full continuation pipeline for that stage, including stage-specific fields
   (`blocking_reasons` for rd-execute, `recommendation` for rd-evaluate).
   These are NOT parameterized shared references.

3. **rd-agent** gets `workflows/intent-routing.md` and
   `workflows/start-contract.md` (same as v1).

4. **rd-tool-catalog** stays as-is (already has `references/tool-selection.md`).

### Why per-skill workflows instead of shared references first

1. `rd-execute` has a unique blocked verification path with `blocking_reasons`
   that has different failure semantics than the other three stages. Burying
   this in a shared parameterization table (v1's approach) flattens the
   contract. The blocked path (current SKILL.md lines 34, 43, 68) includes:
   - A dual outcome ("hand a successful path to `rd-evaluate` **or** publish
     blocked verification with explicit blocking reasons")
   - A conditional field ("provide it only when the verification step must stop
     as blocked, and leave it absent or empty for normal completion")
   - An extra failure recovery step ("ask only for the blocking reasons that
     cannot be derived from current verification state")
   - A unique outcome state (`blocked`) not present in any other stage skill.

2. `rd-evaluate` has branching `recommendation` (continue/stop) that
   determines which skill comes next (`rd-propose` for continue, none for
   stop). This branching logic does not exist in any other stage skill.
   Parameterizing it as `{next_skill}` hides the decision. The branching
   shows in:
   - Required field semantics ("with the exact public values `continue` and
     `stop`")
   - Outcome guide branching ("completed with `continue`: the next high-level
     action is `rd-propose`" vs "completed with `stop`: stop the loop")
   - Success contract ("return a concrete branch outcome: continue back to
     framing or stop the loop")

3. The installer's `_install_skill_support_files()` handles per-skill
   subdirectories already. There is no cost savings from sharing a directory.

4. After all 4 stage skills have their own `workflows/continue.md`, a LATER
   deduplication pass can extract truly identical prose into shared references
   with confidence, because we will know exactly which lines are truly shared
   vs stage-specific.

### Target directory shapes

```
skills/rd-propose/
  SKILL.md
  workflows/
    continue.md           # framing continuation pipeline

skills/rd-code/
  SKILL.md
  workflows/
    continue.md           # build continuation pipeline

skills/rd-execute/
  SKILL.md
  workflows/
    continue.md           # verify continuation pipeline + blocking_reasons

skills/rd-evaluate/
  SKILL.md
  workflows/
    continue.md           # synthesize continuation pipeline + recommendation

skills/rd-agent/
  SKILL.md
  workflows/
    intent-routing.md     # state inspection, paused-run detection, routing reply
    start-contract.md     # minimum/recommended payload, stop behavior
  references/
    failure-routing.md    # missing-field inspection, state-first recovery

skills/rd-tool-catalog/
  SKILL.md                # minor polish only
  references/
    tool-selection.md     # already exists, no changes
```

---

## Part 2: Extraction Map (per skill)

### rd-propose `workflows/continue.md`

**Source sections from `skills/rd-propose/SKILL.md`:**

| Section | Current content | Destination |
|---------|----------------|-------------|
| `## Continue contract` (lines 31-35) | "continue a paused run inside one known step", operator-facing job, high-level skill layer | `workflows/continue.md` |
| `## Required fields` (lines 37-42) | `run_id`, `branch_id`, `summary`, `artifact_ids` with per-field descriptions | `workflows/continue.md` |
| `## If information is missing` (lines 44-49) | inspect state, surface missing, ask operator, rd-tool-catalog escalation | `workflows/continue.md` |

**This file OWNS:**

- Continue-contract framing: "continue a paused run inside the known framing
  step"
- Required fields: `run_id`, `branch_id`, `summary`, `artifact_ids` (no
  extra fields)
- Missing-field recovery: inspect state -> surface missing -> ask operator ->
  rd-tool-catalog escalation
- Handoff target: `rd-code`

**This file does NOT own:**

- Stage routing (stays in SKILL.md `## When to use` / `## When not to use`)
- Tool catalog routing (stays in SKILL.md `## When to route to rd-tool-catalog`)
- Outcome guide (stays in SKILL.md)
- Failure handling for wrong-stage routing (stays in SKILL.md `## Failure handling`)

### rd-code `workflows/continue.md`

Same structure as rd-propose, with these substitutions:

| Parameter | rd-propose value | rd-code value |
|-----------|-----------------|---------------|
| stage name | framing | build |
| next skill | rd-code | rd-execute |

No extra fields. The extraction covers `## Continue contract` (lines 31-35),
`## Required fields` (lines 37-42), and `## If information is missing`
(lines 44-49) from `skills/rd-code/SKILL.md`.

### rd-execute `workflows/continue.md`

Same structure as rd-propose, **PLUS** stage-specific content:

**Source sections from `skills/rd-execute/SKILL.md`:**

| Section | Lines | Extra content vs rd-propose |
|---------|-------|-----------------------------|
| `## Continue contract` | 31-35 | Dual outcome: "hand a successful path to `rd-evaluate` **or** publish blocked verification" |
| `## Required fields` | 37-43 | Extra field: `blocking_reasons` with conditional semantics |
| `## If information is missing` | 45-50 | Extra recovery: "resolved verification payload **or** blocking reasons" |

**Stage-specific field: `blocking_reasons`**

This file must fully describe:

- When to provide `blocking_reasons`: "only when the verification step must
  stop as blocked"
- When to leave it absent: "leave it absent or empty for normal completion"
- The dual outcome path: successful -> `rd-evaluate` handoff vs blocked ->
  publish explicit blocking reasons
- The extra failure recovery step from SKILL.md line 68: "If the blocked path
  is required but `blocking_reasons` is still unresolved after inspection,
  ask only for the blocking reasons that cannot be derived from current
  verification state"

**This content is NOT abstracted behind a shared parameterization table.**
The blocked verification path has different failure semantics than any other
stage. Writing it in full in this file ensures an executor reading only
`rd-execute/workflows/continue.md` gets the complete picture.

### rd-evaluate `workflows/continue.md`

Same structure as rd-propose, **PLUS** stage-specific content:

**Source sections from `skills/rd-evaluate/SKILL.md`:**

| Section | Lines | Extra content vs rd-propose |
|---------|-------|-----------------------------|
| `## Continue contract` | 31-35 | Branch decision outcome: "return the branch decision as `continue` or `stop`" |
| `## Required fields` | 37-43 | Extra field: `recommendation` with public values `continue` and `stop` |
| `## If information is missing` | 45-50 | Recovery target: "resolved synthesize continuation payload" |

**Stage-specific field: `recommendation`**

This file must fully describe:

- The exact public values: `continue` and `stop`
- The branching next-skill logic:
  - `continue` -> next high-level action is `rd-propose`
  - `stop` -> stop the loop, no next stage skill
- Why this branching exists: synthesize is the final stage and must decide
  whether the loop iterates or terminates

**This branching logic is NOT abstracted behind a `{next_skill}` parameter.**
The continue/stop decision is semantically different from the linear handoffs
in rd-propose, rd-code, and rd-execute. Writing it in full prevents an
executor from treating it as a simple variable substitution.

### rd-agent `workflows/intent-routing.md`

**Source sections from `skills/rd-agent/SKILL.md`:**

| Section | Lines | Content |
|---------|-------|---------|
| `## Intent-first routing` | 36-51 | State inspection logic, paused-run detection, routing reply format (4+2 fields), preflight-blocks-recommended-path rule, operator-facing conciseness rule |
| `## Paused-run continuation preference` | 53-62 | run_id/branch_id/stage surfacing, stage-to-skill mapping, preflight-fail handling, new-run-as-fallback rule, detail_hint vs next_step_detail selection |

**Scope boundary:**

- **Owns:** state inspection, paused-run detection, routing reply format
  (`current_state`, `routing_reason`, `exact_next_action`,
  `recommended_next_skill`), optional detail fields (`next_step_detail`,
  `detail_hint`), preflight gate interaction, stage-to-skill continuation
  mapping
- **Does NOT own:** stage-level continuation details (those live in each
  stage skill's `workflows/continue.md`), tool selection (that lives in
  rd-tool-catalog), start payload validation (that lives in
  `workflows/start-contract.md`)

### rd-agent `workflows/start-contract.md`

**Source sections from `skills/rd-agent/SKILL.md`:**

| Section | Lines | Content |
|---------|-------|---------|
| `## Minimum start contract` | 79-83 | Strict minimum fields, first-step payload explanation, fresh-start path |
| `## Recommended multi-branch contract` | 85-103 | Skill-first progression, optional control fields, branch_hypotheses, example payload shape |
| `## Default stop behavior` | 105-111 | gated + max_stage_iterations=1, awaiting_operator, human review pause, continuous unattended alternative |

**Scope boundary:**

- **Owns:** minimum vs recommended payload definition, example shape, field
  validation order, stop behavior after start, execution mode semantics
- **Does NOT own:** stage execution, branch lifecycle, intent routing,
  failure recovery

### rd-agent `references/failure-routing.md`

**Source sections from `skills/rd-agent/SKILL.md`:**

| Section | Lines | Content |
|---------|-------|---------|
| `## Failure handling` | 126-131 | Missing inputs -> inspect state -> surface missing -> ask operator; stage-specific -> route to stage skill; inspection-only -> rd-tool-catalog |
| `## If information is missing` | 133-138 | Inspect before asking, surface exact missing values, only ask for underivable values, route stage-specific tasks to stage skill |

**Scope boundary:**

- **Owns:** missing-field inspection protocol, state-first recovery,
  route-to-correct-stage logic, rd-tool-catalog escalation decision
- **Does NOT own:** stage-level failure handling (each stage skill has its
  own `## Failure handling`), start contract validation

### SKILL.md thinning rules

For each stage skill, the thinned SKILL.md must:

1. **KEEP:** frontmatter, description, Tool execution context, Trigger
   requests, When to use, When not to use, When to route to rd-tool-catalog,
   Failure handling (wrong-stage routing only, not missing-field recovery),
   Output, Outcome guide, Success contract.

2. **REMOVE:** `## Continue contract`, `## Required fields`,
   `## If information is missing` sections (these move to
   `workflows/continue.md`).

3. **ADD:** Conditional load instruction for `workflows/continue.md`:

   ```markdown
   ## Internal workflows

   - Load `workflows/continue.md` when continuing a paused {stage_name} step
     with known `run_id` and `branch_id`.
   ```

4. **ADD:** Strengthened `## When not to use` routing lines:

   ```markdown
   - If blocked, route to: `rd-agent` for full-loop restart, or the correct
     stage skill if the branch is in another stage.
   - If state absent, fresh-start only: do not fabricate continuation
     context; route to `rd-agent` for the minimum start contract.
   ```

For rd-agent, the thinned SKILL.md must:

1. **KEEP:** frontmatter, description, Tool execution context, Trigger
   requests, When to use, Required fields, Optional fields, When to route to
   rd-tool-catalog, When not to use, Output, Success contract.

2. **REMOVE:** `## Intent-first routing`, `## Paused-run continuation
   preference` (move to `workflows/intent-routing.md`), `## Minimum start
   contract`, `## Recommended multi-branch contract`, `## Default stop
   behavior` (move to `workflows/start-contract.md`), `## Failure handling`,
   `## If information is missing` (move to `references/failure-routing.md`).

3. **ADD:** Conditional load instructions:

   ```markdown
   ## Internal workflows

   - Load `workflows/intent-routing.md` when processing plain-language intent
     or detecting paused-run continuation.
   - Load `workflows/start-contract.md` when the operator needs the start
     payload, stop behavior, or example shape.

   ## References

   - Load `references/failure-routing.md` when handling missing inputs,
     routing failures, or deciding between stage skills and rd-tool-catalog.
   ```

4. **ADD:** Strengthened `## When not to use`:

   ```markdown
   - If blocked, route to: the corresponding stage skill (`rd-propose`,
     `rd-code`, `rd-execute`, `rd-evaluate`) or `rd-tool-catalog` for
     inspection-only tasks.
   - If state absent, fresh-start only: do not search other repos or `HOME`;
     stay on the minimum start contract path.
   ```

---

## Part 3: Test Strategy

### Gate 1: Existing pytest suite (MANDATORY, no exceptions)

Before ANY wave starts and after EVERY wave completes:

```bash
uv run pytest \
  tests/test_phase18_skill_installation.py \
  tests/test_phase20_stage_skill_contracts.py \
  tests/test_phase20_rd_agent_skill_contract.py \
  tests/test_phase14_stage_skills.py \
  tests/test_phase14_skill_agent.py \
  -x
```

If any test fails, the wave is RED. Fix before proceeding.

**CRITICAL: Test updates required for stage skill extraction**

`test_phase20_stage_skill_contracts.py` asserts specific text patterns exist
in SKILL.md. When we extract `## Continue contract`, `## Required fields`,
and `## If information is missing` sections from SKILL.md into
`workflows/continue.md`, these tests will break.

**Resolution: Option A (preferred) -- update tests to check the correct file**

Update the test helper and assertions to read continuation contracts from
`workflows/continue.md` instead of SKILL.md for the extracted sections. The
test still asserts the same contracts exist; it just reads from a different
file.

Specifically, these test functions must be updated:

| Test function | Current assertion target | New assertion target |
|---------------|------------------------|---------------------|
| `test_stage_skills_share_continuation_skeleton` | SKILL.md for `"## Continue contract"`, `"## Required fields"`, `"## If information is missing"`, field backticks | `workflows/continue.md` for all these patterns |
| `test_stage_skills_document_exact_special_fields` | SKILL.md for `"blocking_reasons"`, `"recommendation"`, `"continue"`, `"stop"` | `workflows/continue.md` for `blocking_reasons` and `recommendation`; SKILL.md still has `continue`/`stop` in Outcome guide |
| `test_stage_skills_require_agent_led_missing_field_handling` | SKILL.md for `"inspect current run"`, `"surface the exact missing"`, `"Ask the operator"` | `workflows/continue.md` for these patterns |
| `test_stage_skills_document_continue_contract_as_paused_run_flow` | SKILL.md for `"continue a paused run"`, `"rather than restarting"`, `"current-step"` | `workflows/continue.md` for these patterns |

Tests that should **NOT** change (assertions still in SKILL.md):

| Test function | Why unchanged |
|---------------|--------------|
| `test_stage_skills_keep_tool_catalog_as_agent_side_escalation_only` | `## Tool execution context`, `## When to route to rd-tool-catalog` stay in SKILL.md |
| `test_stage_skills_point_to_the_next_high_level_action` | `## Outcome guide` stays in SKILL.md |
| `test_stage_skills_cover_reuse_review_and_replay_outcomes` | `## Outcome guide` stays in SKILL.md |
| `test_stage_skill_outcome_guides_lock_stage_specific_handoffs` | `## Outcome guide` stays in SKILL.md |

**Implementation pattern for updated tests:**

```python
REPO_ROOT = Path(__file__).resolve().parents[1]

STAGE_SKILLS = {
    "rd-propose": REPO_ROOT / "skills" / "rd-propose" / "SKILL.md",
    "rd-code": REPO_ROOT / "skills" / "rd-code" / "SKILL.md",
    "rd-execute": REPO_ROOT / "skills" / "rd-execute" / "SKILL.md",
    "rd-evaluate": REPO_ROOT / "skills" / "rd-evaluate" / "SKILL.md",
}

STAGE_CONTINUE_WORKFLOWS = {
    "rd-propose": REPO_ROOT / "skills" / "rd-propose" / "workflows" / "continue.md",
    "rd-code": REPO_ROOT / "skills" / "rd-code" / "workflows" / "continue.md",
    "rd-execute": REPO_ROOT / "skills" / "rd-execute" / "workflows" / "continue.md",
    "rd-evaluate": REPO_ROOT / "skills" / "rd-evaluate" / "workflows" / "continue.md",
}

def _read_continue_workflow(skill_name: str) -> str:
    return STAGE_CONTINUE_WORKFLOWS[skill_name].read_text()

def _all_continue_texts() -> list[str]:
    return [_read_continue_workflow(name) for name in STAGE_CONTINUE_WORKFLOWS]
```

Then assertions that currently read from `_all_stage_texts()` for extracted
content should read from `_all_continue_texts()` instead.

### Gate 2: Installed-skill smoke test (NEW in v2)

After each wave that modifies skill directories, run a real install and
verify the installed skill can resolve its workflows and references:

```python
# Pseudocode for the smoke test (can be a new test function or script)
import tempfile
from v3.devtools.skill_install import install_agent_skills, discover_repo_root

with tempfile.TemporaryDirectory() as tmp:
    repo_root = discover_repo_root()
    for runtime in ("claude", "codex"):
        records = install_agent_skills(
            runtime=runtime, scope="local", mode="link",
            repo_root=repo_root, home=tmp,
        )
        for record in records:
            if record.action == "linked":
                dest = record.destination
                skill_source = repo_root / "skills" / record.skill_name
                # Verify workflows/ dir was symlinked if source has one
                if (skill_source / "workflows").is_dir():
                    assert (dest / "workflows").is_symlink() or (dest / "workflows").is_dir()
                    for wf in (skill_source / "workflows").iterdir():
                        assert (dest / "workflows" / wf.name).exists(), \
                            f"Missing installed workflow: {wf.name} for {record.skill_name}"
                # Verify references/ dir was symlinked if source has one
                if (skill_source / "references").is_dir():
                    assert (dest / "references").is_symlink() or (dest / "references").is_dir()
                # Verify SKILL.md still has installed runtime bundle section
                text = (dest / "SKILL.md").read_text()
                assert "Installed runtime bundle" in text
```

This test must pass for BOTH `runtime="claude"` and `runtime="codex"`.

### Gate 3: Advisory checks (NOT gates, just metrics)

Line counts, duplication counts, and structural grep checks from v1 Part 4
are retained as advisory information. They are reported but do NOT block
the wave. The real gates are Gate 1 and Gate 2.

Advisory commands (run after each wave for reporting):

```bash
# Line counts (advisory, not a hard gate)
wc -l skills/*/SKILL.md

# Duplication check after stage-name normalization (advisory)
for a in rd-propose rd-code rd-execute rd-evaluate; do
  for b in rd-propose rd-code rd-execute rd-evaluate; do
    if [ "$a" \< "$b" ]; then
      comm -12 \
        <(sed 's/framing\|build\|verify\|synthesize/{stage}/g' "skills/$a/SKILL.md" | sort -u) \
        <(sed 's/framing\|build\|verify\|synthesize/{stage}/g' "skills/$b/SKILL.md" | sort -u) \
      | wc -l | xargs -I{} echo "$a vs $b: {} shared lines"
    fi
  done
done
```

---

## Part 4: Execution Waves

### Wave 0: Proof-of-concept with rd-propose

v1 started with infrastructure (directories, symlinks, shared refs). v2
starts with ONE skill to prove the pattern works end-to-end before touching
the other three.

**Steps:**

1. Create `skills/rd-propose/workflows/` directory.

2. Create `skills/rd-propose/workflows/continue.md` with content extracted
   from rd-propose SKILL.md sections `## Continue contract` (lines 31-35),
   `## Required fields` (lines 37-42), `## If information is missing`
   (lines 44-49).

3. Thin rd-propose SKILL.md: remove extracted sections, add `## Internal
   workflows` conditional load instruction, add strengthened `## When not to
   use` routing lines.

4. Update `test_phase20_stage_skill_contracts.py`:
   - Add `STAGE_CONTINUE_WORKFLOWS` dict and `_read_continue_workflow()` /
     `_all_continue_texts()` helpers.
   - Update `test_stage_skills_share_continuation_skeleton` to check
     `workflows/continue.md` for rd-propose, SKILL.md for the other three
     (they have not been extracted yet).
   - Update `test_stage_skills_require_agent_led_missing_field_handling` same
     split.
   - Update `test_stage_skills_document_continue_contract_as_paused_run_flow`
     same split.

5. Run Gate 1 (all existing tests pass).

6. Run Gate 2 (installed rd-propose resolves `workflows/continue.md` in both
   `.claude` and `.codex`).

**Verification:** If Wave 0 passes both gates, the pattern is proven. If it
fails, we know before touching the other 3 skills.

### Wave 1: Remaining stage skills (rd-code, rd-execute, rd-evaluate)

Can execute all three in parallel since they have no inter-dependencies.

**Steps per skill:**

1. Create `skills/{name}/workflows/` directory.

2. Create `skills/{name}/workflows/continue.md` with stage-specific content:
   - **rd-code:** same pattern as rd-propose, with build/rd-execute
     substitutions.
   - **rd-execute:** include `blocking_reasons` field semantics, conditional
     provision rule, dual outcome path, and the extra failure recovery step
     for blocked verification path **IN FULL** -- not behind a
     parameterization table.
   - **rd-evaluate:** include `recommendation` field semantics, exact public
     values `continue` and `stop`, and the branching next-skill logic
     (`rd-propose` for continue, none for stop) **IN FULL** -- not behind a
     `{next_skill}` variable.

3. Thin SKILL.md: same pattern as Wave 0 for each skill.

4. Update test assertions to read from `workflows/continue.md` for all four
   stage skills (now that all four have been extracted, the test helpers can
   use `_all_continue_texts()` uniformly).

5. Run Gate 1 + Gate 2 after all three are complete.

### Wave 2: rd-agent thinning

**Steps:**

1. Create `skills/rd-agent/workflows/` directory.
2. Create `skills/rd-agent/references/` directory.

3. Create `skills/rd-agent/workflows/intent-routing.md` from SKILL.md
   sections `## Intent-first routing` (lines 36-51) and `## Paused-run
   continuation preference` (lines 53-62).

4. Create `skills/rd-agent/workflows/start-contract.md` from SKILL.md
   sections `## Minimum start contract` (lines 79-83), `## Recommended
   multi-branch contract` (lines 85-103), `## Default stop behavior`
   (lines 105-111).

5. Create `skills/rd-agent/references/failure-routing.md` from SKILL.md
   sections `## Failure handling` (lines 126-131) and `## If information is
   missing` (lines 133-138).

6. Thin rd-agent SKILL.md: remove extracted sections, add `## Internal
   workflows` and `## References` conditional load instructions, add
   strengthened `## When not to use` routing lines.

7. Update `test_phase20_rd_agent_skill_contract.py`:
   - `test_rd_agent_skill_separates_minimum_and_recommended_paths` should read
     from `workflows/start-contract.md`.
   - `test_rd_agent_skill_explains_default_pause_behavior_in_plain_language`
     should read from `workflows/start-contract.md`.
   - `test_rd_agent_skill_requires_agent_led_missing_field_recovery` should
     read from `references/failure-routing.md`.
   - Tests that assert on SKILL.md sections that stay (Required fields,
     Optional fields, Tool execution context, When to route, Success
     contract) should NOT change.

8. Run Gate 1 + Gate 2.

### Wave 3: rd-tool-catalog polish (trivial)

**Steps:**

1. Add strengthened `## When not to use` routing lines to rd-tool-catalog
   SKILL.md:

   ```markdown
   - If blocked, route to: `rd-agent` for orchestration, or the correct
     stage skill if the caller knows which stage they need.
   - If state absent: this skill does not require persisted V3 state to
     function; it operates on catalog metadata only.
   ```

2. Run Gate 1 + Gate 2.

### Wave 4: Optional shared-reference deduplication

**ONLY after Waves 0-3 are green.**

1. Diff the four `workflows/continue.md` files to identify truly identical
   lines.

2. If >60% of lines are identical after stage-name normalization, CONSIDER
   extracting a shared reference. If not, leave per-skill.

3. If extracting shared reference:
   - Create `skills/_shared/references/` directory.
   - Add a symlink `.claude/skills/_shared -> skills/_shared`.
   - Move only the truly identical continuation prose into
     `skills/_shared/references/stage-continuation-contract.md`.
   - Keep stage-specific extra fields and failure paths in per-skill
     `workflows/continue.md` even if the shared reference is created.

4. This wave is **OPTIONAL**. The refactoring is complete and correct after
   Wave 3.

---

## Part 5: Constraints and Anti-Patterns

### Line count is advisory, not a gate

Real gates for SKILL.md quality:

- **Single responsibility:** SKILL.md should be about triggering, boundary,
  routing. Not about continuation pipeline internals.
- **Conditional loading:** all "Load X" references must have a "when Y"
  condition. No SKILL.md should unconditionally load all references at the
  top.
- **Explicit route-out:** every `## When not to use` must name specific
  alternative skills by name, not "the appropriate skill."
- **No duplicated contract prose:** the same continuation contract text must
  not appear in two SKILL.md files verbatim after extraction.
- **Deterministic execution root:** `## Tool execution context` must point
  to a concrete path (`standalone V3 repo root` or `installed standalone V3
  runtime bundle root`).

### Stage-specific fields are never shared

`rd-execute`'s `blocking_reasons` and `rd-evaluate`'s `recommendation` MUST
stay in their respective `workflows/continue.md` files. They must NOT be
moved to a shared reference parameterization table.

Universal core fields (`run_id`, `branch_id`, `summary`, `artifact_ids`)
MAY be shared in Wave 4 if deduplication proves worthwhile.

### Backward compatibility

No migration needed for cached sessions. The refactoring is structural, not
behavioral. Thinned SKILL.md files still contain the same boundary
declarations (When to use, When not to use, Tool execution context, Output,
Success contract). The internal pipeline detail that was always informational
rather than contractual moves to `workflows/continue.md`.

### Progressive disclosure is the key constraint

The entire refactoring is pointless if thinned SKILL.md files just add
unconditional `@` loads at the top that pull everything in. The critical
constraint is:

- SKILL.md uses conditional loading: "Load X when Y"
- Workflow files are loaded only when the agent reaches that execution step
- References are loaded only when the agent needs that specific decision tree

If this constraint is violated, the refactoring merely moves text around
without reducing the context burden. Every executor must verify: "Does NOT
unconditionally load all references at the top."

---

## Part 6: How This Blueprint Addresses v1 Problems

| Problem | v1 Approach | v2 Fix |
|---------|------------|--------|
| **P1-1: Wrong installation model** | Proposed `_shared` symlink as Wave 0; assumed a new `.claude/skills/_shared -> skills/_shared` symlink was required before any skill work | Leverages existing `_install_skill_support_files()` at line 247 of `skill_install.py`; per-skill `workflows/` directories are installed automatically with zero installer changes |
| **P1-2: Stage skills only moved prose to shared refs** | Four stage skills extracted identical sections to `_shared/references/stage-continuation-contract.md` with a parameterization table; the stage skills became empty shells referencing shared text | Each stage skill builds its own `workflows/continue.md` owning the full continuation pipeline including stage-specific fields and failure paths; stage skills remain self-contained |
| **P1-3: Verification was grep/wc line counting** | Wave 5 used `wc -l < 80`, duplication grep, structural checks as hard gates | Gate 1: existing `pytest` suite is mandatory and runs before and after every wave. Gate 2: installed-skill smoke test verifies `workflows/` resolution in both runtimes. Gate 3: line counts are advisory only |
| **P2-1: Shared parameterization hides contracts** | `blocking_reasons` and `recommendation` appeared in a shared parameterization table as `{extra_fields}` with a `{next_skill}` template variable | Stage-specific fields stay in per-skill `workflows/continue.md`. `blocking_reasons`'s dual outcome and conditional provision are written in full. `recommendation`'s continue/stop branching is written in full. No template variables |
| **P2-2: Line count as hard gate** | `wc -l` must be < 80 was a blocking verification step | Line count is advisory. Real gates are single-responsibility, conditional-loading, explicit-route-out, no-duplication, and deterministic-execution-root quality checks, enforced by the pytest suite |

---

## Part 7: Test Diagram Satisfaction

```text
public skill
  -> load internal workflow?
     YES: workflows/continue.md loaded conditionally
          "when continuing a paused {stage_name} step with known run_id and branch_id"
     -> state/preflight routing
        YES: SKILL.md keeps "## When to use" / "## When not to use" with explicit routing
             Added: "If blocked, route to:" with named skills
             Added: "If state absent, fresh-start only:" with concrete behavior
     -> stage continuation contract
        YES: workflows/continue.md owns run_id/branch_id/summary/artifact_ids + stage extras
             rd-execute: blocking_reasons in full with dual outcome and conditional provision
             rd-evaluate: recommendation in full with continue/stop branching
     -> direct-tool downshift
        YES: SKILL.md keeps "## When to route to rd-tool-catalog" with agent-side escalation
             "keep the operator on the {skill} path rather than defaulting to manual tool browsing"
  -> installed generated skill dir
     -> shared refs/workflows resolve?
        YES: _install_skill_support_files() at line 247 symlinks/copies workflows/
             directory automatically for any skill that has one
        HOW: iterates all children of source_dir except SKILL.md; workflows/ is a child
     -> runtime bundle root stays correct?
        YES: _render_installed_skill() at line 265 appends bundle_root
             Line 279: "Relative resources for this installed skill still resolve
             inside {bundle_root / 'skills' / source_dir.name}"
        NO CHANGE: to the _render_installed_skill() mechanism
```

**Required tests and how they are satisfied:**

| Requirement | Mechanism |
|-------------|-----------|
| Source skill contract tests continue green | Gate 1: existing pytest suite with test updates for new file locations (Option A) |
| Installed skill can resolve workflows and references | Gate 2: new smoke test installs to temp dir and verifies `workflows/` directory presence |
| Both `.claude` and `.codex` verified | Gate 2 runs both `runtime="claude"` and `runtime="codex"` |
| `rd-execute` blocked path not flattened | Per-skill `workflows/continue.md` owns `blocking_reasons` in full, not shared parameterization |
| `rd-evaluate` branching path not flattened | Per-skill `workflows/continue.md` owns `recommendation` continue/stop branching in full |
| No unconditional loading | All `## Internal workflows` sections use "Load X **when** Y" conditional language |
| Strengthened negative routing | Every SKILL.md gets "If blocked, route to:" and "If state absent" fixed-format lines |

---

## Appendix: Quick Reference for Executors

### File inventory after all waves complete

| File | Created in | Content source |
|------|-----------|---------------|
| `skills/rd-propose/workflows/continue.md` | Wave 0 | rd-propose SKILL.md lines 31-49 |
| `skills/rd-code/workflows/continue.md` | Wave 1 | rd-code SKILL.md lines 31-49 |
| `skills/rd-execute/workflows/continue.md` | Wave 1 | rd-execute SKILL.md lines 31-50 |
| `skills/rd-evaluate/workflows/continue.md` | Wave 1 | rd-evaluate SKILL.md lines 31-50 |
| `skills/rd-agent/workflows/intent-routing.md` | Wave 2 | rd-agent SKILL.md lines 36-62 |
| `skills/rd-agent/workflows/start-contract.md` | Wave 2 | rd-agent SKILL.md lines 79-111 |
| `skills/rd-agent/references/failure-routing.md` | Wave 2 | rd-agent SKILL.md lines 126-138 |

### Test files requiring updates

| Test file | Wave | Changes |
|-----------|------|---------|
| `tests/test_phase20_stage_skill_contracts.py` | Wave 0 (partial), Wave 1 (complete) | Add `STAGE_CONTINUE_WORKFLOWS` dict, update 4 test functions to read from `workflows/continue.md` |
| `tests/test_phase20_rd_agent_skill_contract.py` | Wave 2 | Update 3 test functions to read from `workflows/start-contract.md` or `references/failure-routing.md` |

### Commands to run between waves

```bash
# Gate 1: Mandatory pytest (run before AND after each wave)
uv run pytest tests/test_phase18_skill_installation.py \
  tests/test_phase20_stage_skill_contracts.py \
  tests/test_phase20_rd_agent_skill_contract.py \
  tests/test_phase14_stage_skills.py \
  tests/test_phase14_skill_agent.py -x

# Gate 2: Installed-skill smoke test (run after each wave that modifies skills)
uv run pytest tests/test_installed_skill_workflows.py -x  # or inline script

# Gate 3: Advisory line counts (informational only)
wc -l skills/*/SKILL.md
```
