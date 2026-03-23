---
phase: quick
plan: 260323-wsb
type: execute
wave: 1
depends_on: []
files_modified:
  # Wave 0 (Task 1)
  - skills/rd-propose/workflows/continue.md
  - skills/rd-propose/SKILL.md
  - tests/test_phase20_stage_skill_contracts.py
  - tests/test_installed_skill_workflows.py
  # Wave 1 (Task 2)
  - skills/rd-code/workflows/continue.md
  - skills/rd-code/SKILL.md
  - skills/rd-execute/workflows/continue.md
  - skills/rd-execute/SKILL.md
  - skills/rd-evaluate/workflows/continue.md
  - skills/rd-evaluate/SKILL.md
  # Wave 2+3 (Task 3)
  - skills/rd-agent/workflows/intent-routing.md
  - skills/rd-agent/workflows/start-contract.md
  - skills/rd-agent/references/failure-routing.md
  - skills/rd-agent/SKILL.md
  - skills/rd-tool-catalog/SKILL.md
  - tests/test_phase20_rd_agent_skill_contract.py
autonomous: true
requirements: [BLUEPRINT-v2-wave-0, BLUEPRINT-v2-wave-1, BLUEPRINT-v2-wave-2, BLUEPRINT-v2-wave-3]

must_haves:
  truths:
    - "All 37 existing tests pass after every wave (Gate 1 never breaks)"
    - "Installed skills resolve workflows/ and references/ in both claude and codex runtimes (Gate 2)"
    - "Stage skill SKILL.md files no longer contain Continue contract, Required fields, or If information is missing sections"
    - "rd-agent SKILL.md no longer contains Intent-first routing, Minimum start contract, or Failure handling sections"
    - "All conditional load instructions use 'Load X when Y' format (progressive disclosure preserved)"
  artifacts:
    - path: "skills/rd-propose/workflows/continue.md"
      provides: "Framing continuation pipeline"
    - path: "skills/rd-code/workflows/continue.md"
      provides: "Build continuation pipeline"
    - path: "skills/rd-execute/workflows/continue.md"
      provides: "Verify continuation pipeline with blocking_reasons"
    - path: "skills/rd-evaluate/workflows/continue.md"
      provides: "Synthesize continuation pipeline with recommendation"
    - path: "skills/rd-agent/workflows/intent-routing.md"
      provides: "State inspection and paused-run detection"
    - path: "skills/rd-agent/workflows/start-contract.md"
      provides: "Minimum/recommended payload and stop behavior"
    - path: "skills/rd-agent/references/failure-routing.md"
      provides: "Missing-field recovery and route-to-correct-stage logic"
    - path: "tests/test_installed_skill_workflows.py"
      provides: "Gate 2 smoke test for installed workflow resolution"
  key_links:
    - from: "skills/rd-propose/SKILL.md"
      to: "skills/rd-propose/workflows/continue.md"
      via: "Internal workflows conditional load"
      pattern: "Load `workflows/continue.md` when"
    - from: "skills/rd-agent/SKILL.md"
      to: "skills/rd-agent/workflows/intent-routing.md"
      via: "Internal workflows conditional load"
      pattern: "Load `workflows/intent-routing.md` when"
    - from: "tests/test_phase20_stage_skill_contracts.py"
      to: "skills/*/workflows/continue.md"
      via: "STAGE_CONTINUE_WORKFLOWS dict"
      pattern: "_all_continue_texts"
---

<objective>
Execute BLUEPRINT v2 Waves 0-3: extract continuation pipelines from stage skill
SKILL.md files into per-skill `workflows/continue.md`, extract rd-agent internals
into `workflows/` and `references/`, thin all SKILL.md files, update tests, and
verify with Gate 1 (37 existing tests) + Gate 2 (installed-skill smoke test).

Purpose: Reduce SKILL.md context burden by moving internal pipeline detail to
conditionally-loaded workflow files while preserving all regression contracts.

Output: 7 new workflow/reference files, 6 thinned SKILL.md files, 1 new Gate 2
test file, 2 updated test files, all gates green.
</objective>

<execution_context>
@/Users/michael-liang/.claude/get-shit-done/workflows/execute-plan.md
@/Users/michael-liang/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260323-r08-blueprint-v2-installer-surface-skill/BLUEPRINT-v2.md
@skills/rd-propose/SKILL.md
@skills/rd-code/SKILL.md
@skills/rd-execute/SKILL.md
@skills/rd-evaluate/SKILL.md
@skills/rd-agent/SKILL.md
@skills/rd-tool-catalog/SKILL.md
@tests/test_phase20_stage_skill_contracts.py
@tests/test_phase20_rd_agent_skill_contract.py
@tests/test_phase18_skill_installation.py
@v3/devtools/skill_install.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wave 0 -- rd-propose proof-of-concept + Gate 2 test</name>
  <files>
    skills/rd-propose/workflows/continue.md
    skills/rd-propose/SKILL.md
    tests/test_phase20_stage_skill_contracts.py
    tests/test_installed_skill_workflows.py
  </files>
  <action>
**Step 1: Create `skills/rd-propose/workflows/continue.md`**

Create directory `skills/rd-propose/workflows/`. Extract content from rd-propose
SKILL.md sections into a new `continue.md`:

```markdown
# Continue contract: rd-propose (framing)

Use this skill to continue a paused run inside one known step, not to restart
the whole standalone flow.

The operator-facing job is: continue the current framing step with the exact
continuation identifiers and payload, then hand off the successful path to
`rd-code`.

Keep the interaction at the high-level skill layer unless the agent must inspect
lower-level state to recover missing continuation details.

## Required fields

- `run_id`: the run identifier for the paused standalone V3 run.
- `branch_id`: the branch identifier that owns the current framing step.
- `summary`: the current-step summary to publish for this framing continuation.
- `artifact_ids`: the current-step artifact identifiers to publish or replay for
  this framing continuation.

## If information is missing

- First inspect current run or branch state instead of asking the operator to
  browse tools manually.
- Then surface the exact missing values, including which field names are still
  absent and which values the agent already derived from current state.
- Ask the operator only for values that cannot already be derived.
- If the agent still needs a direct inspection or recovery primitive, use
  `rd-tool-catalog` as an agent-side escalation path and return with the
  resolved continuation fields.
```

Preserve EXACT prose from the current SKILL.md lines 31-49. The above is the
target content -- copy faithfully from the source SKILL.md, not paraphrased.

**Step 2: Thin `skills/rd-propose/SKILL.md`**

Remove these three sections entirely:
- `## Continue contract` (lines 31-35)
- `## Required fields` (lines 37-42)
- `## If information is missing` (lines 44-49)

Add after `## When to use` (before `## When to route to rd-tool-catalog`):

```markdown
## Internal workflows

- Load `workflows/continue.md` when continuing a paused framing step with known
  `run_id` and `branch_id`.
```

Add to end of existing `## When not to use`:

```markdown
- If blocked, route to: `rd-agent` for full-loop restart, or the correct stage
  skill if the branch is in another stage.
- If state absent, fresh-start only: do not fabricate continuation context;
  route to `rd-agent` for the minimum start contract.
```

**Step 3: Update `tests/test_phase20_stage_skill_contracts.py`**

Add new dict and helpers AFTER the existing `STAGE_SKILLS` dict:

```python
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

Update these 4 test functions to use a SPLIT strategy: check `workflows/continue.md`
for rd-propose (already extracted), but check SKILL.md for the other three
(not yet extracted in Wave 0):

- `test_stage_skills_share_continuation_skeleton`: For rd-propose, read from
  `_read_continue_workflow("rd-propose")` and assert `"## Continue contract"`
  heading is present (the `continue.md` file starts with
  `# Continue contract: rd-propose` so check for `"Continue contract"` without
  the `## ` prefix, OR better: assert `"## Required fields"`,
  `"## If information is missing"`, and the 4 field backticks). For the other
  three skills, keep reading from `_all_stage_texts()` minus rd-propose.
  The `"## Outcome guide"` assertion stays on SKILL.md for all 4.

  Concrete pattern: iterate all 4 skills. For each, pick the correct source:
  `_read_continue_workflow(name)` if `(STAGE_CONTINUE_WORKFLOWS[name]).is_file()`
  else `_read_stage_skill(name)`. Assert continuation patterns on that source.
  Assert `"## Outcome guide"` always on `_read_stage_skill(name)`.

- `test_stage_skills_document_exact_special_fields`: For `blocking_reasons`,
  read from SKILL.md (rd-execute not extracted yet). For `recommendation`,
  `continue`, `stop`, read from SKILL.md (rd-evaluate not extracted yet).
  Same split logic: if workflow file exists, read from it; else read SKILL.md.

- `test_stage_skills_require_agent_led_missing_field_handling`: Same split.
  rd-propose assertions from `workflows/continue.md`, others from SKILL.md.
  NOTE: The assertion text is `"Ask the operator only for values that cannot
  already be derived"` -- the continue.md must contain this exact string.
  Check rd-propose SKILL.md line 48: it says "Ask the operator only for values
  that cannot already be derived." -- copy this exactly.

- `test_stage_skills_document_continue_contract_as_paused_run_flow`: Same split.
  Must find `"continue a paused run"`, `"rather than restarting"` or
  `"not to restart"`, and `"current-step"` in the continue.md for rd-propose.
  Check: SKILL.md line 33 says "not to restart the whole standalone flow" --
  the continue.md must preserve "not to restart" phrasing.

  The split pattern for ALL updated tests is:

  ```python
  def _continuation_text(skill_name: str) -> str:
      """Read continuation contract from workflows/continue.md if it exists, else SKILL.md."""
      wf = STAGE_CONTINUE_WORKFLOWS[skill_name]
      if wf.is_file():
          return wf.read_text()
      return _read_stage_skill(skill_name)
  ```

  Add this one helper and use it in the 4 updated test functions.

**Step 4: Create Gate 2 test `tests/test_installed_skill_workflows.py`**

New test file following the pseudocode from BLUEPRINT-v2 Part 3 Gate 2:

```python
"""Gate 2: Verify installed skills resolve their workflows/ and references/ directories."""

from __future__ import annotations

import tempfile
from pathlib import Path

from v3.devtools.skill_install import discover_repo_root, install_agent_skills


def test_installed_skills_resolve_workflows_and_references() -> None:
    repo_root = discover_repo_root()

    with tempfile.TemporaryDirectory() as tmp:
        for runtime in ("claude", "codex"):
            records = install_agent_skills(
                runtime=runtime,
                scope="local",
                mode="link",
                repo_root=repo_root,
                home=Path(tmp),
            )
            for record in records:
                if record.action != "linked":
                    continue
                dest = record.destination
                skill_source = repo_root / "skills" / record.skill_name

                # Verify workflows/ dir was symlinked if source has one
                if (skill_source / "workflows").is_dir():
                    assert (dest / "workflows").is_symlink() or (
                        dest / "workflows"
                    ).is_dir(), (
                        f"workflows/ not installed for {record.skill_name} ({runtime})"
                    )
                    for wf in sorted((skill_source / "workflows").iterdir()):
                        assert (dest / "workflows" / wf.name).exists(), (
                            f"Missing installed workflow: {wf.name} for {record.skill_name} ({runtime})"
                        )

                # Verify references/ dir was symlinked if source has one
                if (skill_source / "references").is_dir():
                    assert (dest / "references").is_symlink() or (
                        dest / "references"
                    ).is_dir(), (
                        f"references/ not installed for {record.skill_name} ({runtime})"
                    )

                # Verify SKILL.md still has installed runtime bundle section
                text = (dest / "SKILL.md").read_text()
                assert "Installed runtime bundle" in text, (
                    f"Missing runtime bundle section for {record.skill_name} ({runtime})"
                )
```

**Step 5: Run Gate 1 + Gate 2**

```bash
uv run pytest tests/test_phase18_skill_installation.py \
  tests/test_phase20_stage_skill_contracts.py \
  tests/test_phase20_rd_agent_skill_contract.py \
  tests/test_phase14_stage_skills.py \
  tests/test_phase14_skill_agent.py -x

uv run pytest tests/test_installed_skill_workflows.py -x
```

Both must pass. If Gate 1 fails, the continue.md content does not faithfully
reproduce the extracted SKILL.md prose -- fix by comparing exact strings.
  </action>
  <verify>
    <automated>cd /Users/michael-liang/Code/my-RDagent-V3 && uv run pytest tests/test_phase18_skill_installation.py tests/test_phase20_stage_skill_contracts.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase14_stage_skills.py tests/test_phase14_skill_agent.py tests/test_installed_skill_workflows.py -x</automated>
  </verify>
  <done>
    - `skills/rd-propose/workflows/continue.md` exists with full continuation contract
    - `skills/rd-propose/SKILL.md` no longer has ## Continue contract, ## Required fields, ## If information is missing
    - `skills/rd-propose/SKILL.md` has ## Internal workflows with conditional load
    - `skills/rd-propose/SKILL.md` has strengthened ## When not to use lines
    - `tests/test_phase20_stage_skill_contracts.py` has `_continuation_text()` split helper
    - `tests/test_installed_skill_workflows.py` exists and passes
    - Gate 1: all existing tests pass (37+)
    - Gate 2: installed rd-propose resolves workflows/continue.md in both runtimes
  </done>
</task>

<task type="auto">
  <name>Task 2: Wave 1 -- rd-code, rd-execute, rd-evaluate extraction</name>
  <files>
    skills/rd-code/workflows/continue.md
    skills/rd-code/SKILL.md
    skills/rd-execute/workflows/continue.md
    skills/rd-execute/SKILL.md
    skills/rd-evaluate/workflows/continue.md
    skills/rd-evaluate/SKILL.md
    tests/test_phase20_stage_skill_contracts.py
  </files>
  <action>
**For each of rd-code, rd-execute, rd-evaluate, repeat the Wave 0 pattern:**

**A. Create `skills/{name}/workflows/continue.md`**

Create the `workflows/` directory and `continue.md` inside it.

**rd-code `workflows/continue.md`**: Same structure as rd-propose, with:
- Stage name: "build" (not "framing")
- Next skill: `rd-execute` (not `rd-code`)
- Extract from rd-code SKILL.md lines 31-49 (## Continue contract through
  ## If information is missing). Preserve exact prose.
- Title: `# Continue contract: rd-code (build)`

**rd-execute `workflows/continue.md`**: Same base structure PLUS stage-specific
content. Extract from rd-execute SKILL.md lines 31-50:
- Title: `# Continue contract: rd-execute (verify)`
- Stage name: "verify" / "verification"
- Next skill: `rd-evaluate` (for the successful path)
- MUST include the full `blocking_reasons` field with:
  - "provide it only when the verification step must stop as blocked"
  - "leave it absent or empty for normal completion"
  - The dual outcome: "hand a successful path to `rd-evaluate` or publish
    blocked verification with explicit blocking reasons"
- MUST include the extra failure recovery from SKILL.md line 68:
  "If the blocked path is required but `blocking_reasons` is still unresolved
  after inspection, ask only for the blocking reasons that cannot be derived
  from current verification state"
  Place this as an additional bullet in the "## If information is missing"
  section of the continue.md.

**rd-evaluate `workflows/continue.md`**: Same base structure PLUS
stage-specific content. Extract from rd-evaluate SKILL.md lines 31-50:
- Title: `# Continue contract: rd-evaluate (synthesize)`
- Stage name: "synthesize"
- Next skill: branching -- `rd-propose` for `continue`, none for `stop`
- MUST include the full `recommendation` field with:
  - "the exact public values `continue` and `stop`"
  - Branching logic: "completed with `continue`: the next high-level action is
    `rd-propose`" and "completed with `stop`: stop the loop"
- Write the branching in full -- NOT behind a `{next_skill}` variable.

**B. Thin each SKILL.md (same pattern as Wave 0)**

For each of rd-code, rd-execute, rd-evaluate:
1. Remove `## Continue contract`, `## Required fields`,
   `## If information is missing` sections.
2. Add `## Internal workflows` with conditional load instruction using the
   correct stage name:
   - rd-code: "continuing a paused build step"
   - rd-execute: "continuing a paused verify step"
   - rd-evaluate: "continuing a paused synthesize step"
3. Add strengthened `## When not to use` lines (same two lines as rd-propose).

**C. Finalize test updates in `tests/test_phase20_stage_skill_contracts.py`**

Now that ALL four stage skills have `workflows/continue.md`, the
`_continuation_text()` helper from Task 1 will automatically pick up all four
workflow files (since all `.is_file()` checks will return True). No additional
test logic changes needed beyond what Task 1 created -- the split helper
already handles the "file exists -> read workflow, else -> read SKILL.md" logic.

Verify: the `test_stage_skills_document_exact_special_fields` test must now read
`blocking_reasons` from rd-execute's `workflows/continue.md` (not SKILL.md) and
`recommendation`/`continue`/`stop` from rd-evaluate's `workflows/continue.md`.
The `_continuation_text()` helper handles this automatically.

IMPORTANT for `continue`/`stop` assertions: The test currently checks
`evaluate_text` for both `"`continue`"` and `"`stop`"`. After extraction,
`continue` and `stop` appear in BOTH the Outcome guide (stays in SKILL.md) and
the continue.md. The test reads from `_continuation_text()` which returns
continue.md. But the test also needs `continue`/`stop` to be in SKILL.md's
Outcome guide for the `test_stage_skills_point_to_the_next_high_level_action`
test. Verify both sources have these strings.

**D. Run Gate 1 + Gate 2**

```bash
uv run pytest tests/test_phase18_skill_installation.py \
  tests/test_phase20_stage_skill_contracts.py \
  tests/test_phase20_rd_agent_skill_contract.py \
  tests/test_phase14_stage_skills.py \
  tests/test_phase14_skill_agent.py -x

uv run pytest tests/test_installed_skill_workflows.py -x
```
  </action>
  <verify>
    <automated>cd /Users/michael-liang/Code/my-RDagent-V3 && uv run pytest tests/test_phase18_skill_installation.py tests/test_phase20_stage_skill_contracts.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase14_stage_skills.py tests/test_phase14_skill_agent.py tests/test_installed_skill_workflows.py -x</automated>
  </verify>
  <done>
    - All 4 stage skills have `workflows/continue.md` with faithful extractions
    - rd-execute's continue.md has full `blocking_reasons` with dual outcome and extra recovery step
    - rd-evaluate's continue.md has full `recommendation` with continue/stop branching (not parameterized)
    - All 4 stage SKILL.md files no longer have ## Continue contract, ## Required fields, ## If information is missing
    - All 4 stage SKILL.md files have ## Internal workflows with conditional load
    - All 4 stage SKILL.md files have strengthened ## When not to use lines
    - Gate 1: all tests pass
    - Gate 2: all 4 stage skills resolve workflows/ in both runtimes
  </done>
</task>

<task type="auto">
  <name>Task 3: Wave 2+3 -- rd-agent extraction + rd-tool-catalog polish</name>
  <files>
    skills/rd-agent/workflows/intent-routing.md
    skills/rd-agent/workflows/start-contract.md
    skills/rd-agent/references/failure-routing.md
    skills/rd-agent/SKILL.md
    skills/rd-tool-catalog/SKILL.md
    tests/test_phase20_rd_agent_skill_contract.py
  </files>
  <action>
**Wave 2: rd-agent extraction**

**Step 1: Create directories**

```bash
mkdir -p skills/rd-agent/workflows
mkdir -p skills/rd-agent/references
```

**Step 2: Create `skills/rd-agent/workflows/intent-routing.md`**

Extract from rd-agent SKILL.md `## Intent-first routing` (lines 36-51) and
`## Paused-run continuation preference` (lines 53-62). Preserve exact prose.

Title: `# Intent-first routing and paused-run continuation`

Content sections:
- Intent-first routing: plain-language entry, state inspection, paused-run
  preference, 4+2 routing reply fields, preflight-blocks handling, conciseness
- Paused-run continuation preference: run_id/branch_id/stage surfacing,
  stage-to-skill mapping (framing->rd-propose, build->rd-code,
  verify->rd-execute, synthesize->rd-evaluate), preflight-fail handling,
  new-run-as-fallback, detail_hint vs next_step_detail

**Step 3: Create `skills/rd-agent/workflows/start-contract.md`**

Extract from rd-agent SKILL.md `## Minimum start contract` (lines 79-83),
`## Recommended multi-branch contract` (lines 85-103), and
`## Default stop behavior` (lines 105-111). Preserve exact prose including
the example payload shape code block.

Title: `# Start contract and default stop behavior`

Sections:
- `## Minimum start contract`: strict minimum fields, first-step payload
- `## Recommended multi-branch contract`: skill-first progression, optional
  controls, branch_hypotheses, example payload
- `## Default stop behavior`: gated + max_stage_iterations=1, awaiting_operator,
  human review pause, continuous alternative

**Step 4: Create `skills/rd-agent/references/failure-routing.md`**

Extract from rd-agent SKILL.md `## Failure handling` (lines 126-131) and
`## If information is missing` (lines 133-138). Preserve exact prose.

Title: `# Failure routing and missing-field recovery`

Sections:
- `## Failure handling`: missing inputs -> inspect -> surface -> ask;
  stage-specific -> route to stage skill; inspection-only -> rd-tool-catalog
- `## If information is missing`: inspect before asking, surface exact values,
  only ask for underivable values, route stage-specific to stage skill

**Step 5: Thin `skills/rd-agent/SKILL.md`**

Remove these sections:
- `## Intent-first routing` (lines 36-51)
- `## Paused-run continuation preference` (lines 53-62)
- `## Minimum start contract` (lines 79-83)
- `## Recommended multi-branch contract` (lines 85-103)
- `## Default stop behavior` (lines 105-111)
- `## Failure handling` (lines 126-131)
- `## If information is missing` (lines 133-138)

KEEP these sections (they stay in SKILL.md):
- Frontmatter, description, Tool execution context, Trigger requests, When to use
- `## Required fields` (lines 64-71) -- the field list
- `## Optional fields` (lines 73-77)
- `## When to route to rd-tool-catalog`
- `## When not to use`
- `## Output`
- `## Success contract`

Add after `## Optional fields` (before `## When to route to rd-tool-catalog`):

```markdown
## Internal workflows

- Load `workflows/intent-routing.md` when processing plain-language intent or
  detecting paused-run continuation.
- Load `workflows/start-contract.md` when the operator needs the start payload,
  stop behavior, or example shape.

## References

- Load `references/failure-routing.md` when handling missing inputs, routing
  failures, or deciding between stage skills and rd-tool-catalog.
```

Add to end of existing `## When not to use`:

```markdown
- If blocked, route to: the corresponding stage skill (`rd-propose`, `rd-code`,
  `rd-execute`, `rd-evaluate`) or `rd-tool-catalog` for inspection-only tasks.
- If state absent, fresh-start only: do not search other repos or `HOME`; stay
  on the minimum start contract path.
```

**Step 6: Update `tests/test_phase20_rd_agent_skill_contract.py`**

Add file-path constants and helpers at module level:

```python
RD_AGENT_DIR = REPO_ROOT / "skills" / "rd-agent"
RD_AGENT_START_CONTRACT = RD_AGENT_DIR / "workflows" / "start-contract.md"
RD_AGENT_FAILURE_ROUTING = RD_AGENT_DIR / "references" / "failure-routing.md"
```

Update these 3 test functions:

- `test_rd_agent_skill_separates_minimum_and_recommended_paths`:
  Read from `RD_AGENT_START_CONTRACT.read_text()` instead of `_skill_text()`.
  Assert: `"## Minimum start contract"`, `"## Recommended multi-branch contract"`,
  `` "`branch_hypotheses`" ``, `"it is not part of the strict minimum start contract"`,
  `"the first internal step is \`framing\`"`.

- `test_rd_agent_skill_explains_default_pause_behavior_in_plain_language`:
  Read from `RD_AGENT_START_CONTRACT.read_text()` instead of `_skill_text()`.
  Assert all the same strings: `"## Default stop behavior"`,
  `` "`gated + max_stage_iterations=1`" ``, etc.

- `test_rd_agent_skill_requires_agent_led_missing_field_recovery`:
  Read from `RD_AGENT_FAILURE_ROUTING.read_text()` instead of `_skill_text()`.
  Assert: `"## If information is missing"`, `"inspect current run or branch state"`,
  `"surface the exact missing values"`,
  `"Only ask the operator for values that cannot already be derived"`.

Tests that must NOT change (assertions stay on SKILL.md):
- `test_rd_agent_skill_names_minimum_start_contract` (Required/Optional fields stay)
- `test_rd_agent_skill_keeps_required_and_optional_field_layers_distinct`
  (Required/Optional ordering stays -- but NOTE: `## Minimum start contract` is
  removed from SKILL.md, so the `text.index("## Minimum start contract")` line
  will fail. This test must be updated to NOT assert ordering with
  `## Minimum start contract`. Change: remove the
  `minimum_start = text.index("## Minimum start contract")` line and the
  `assert required_start < optional_start < minimum_start` assertion. Replace
  with just `assert required_start < optional_start`.)
- `test_rd_agent_skill_keeps_tool_catalog_as_agent_side_escalation`
- `test_rd_agent_skill_ends_with_explicit_success_contract`

**Wave 3: rd-tool-catalog polish**

**Step 7: Update `skills/rd-tool-catalog/SKILL.md`**

Add to end of existing `## When not to use` section:

```markdown
- If blocked, route to: `rd-agent` for orchestration, or the correct stage skill
  if the caller knows which stage they need.
- If state absent: this skill does not require persisted V3 state to function;
  it operates on catalog metadata only.
```

**Step 8: Run Gate 1 + Gate 2**

```bash
uv run pytest tests/test_phase18_skill_installation.py \
  tests/test_phase20_stage_skill_contracts.py \
  tests/test_phase20_rd_agent_skill_contract.py \
  tests/test_phase14_stage_skills.py \
  tests/test_phase14_skill_agent.py -x

uv run pytest tests/test_installed_skill_workflows.py -x
```

**Step 9: Advisory line counts (informational only, not a gate)**

```bash
wc -l skills/*/SKILL.md
```
  </action>
  <verify>
    <automated>cd /Users/michael-liang/Code/my-RDagent-V3 && uv run pytest tests/test_phase18_skill_installation.py tests/test_phase20_stage_skill_contracts.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase14_stage_skills.py tests/test_phase14_skill_agent.py tests/test_installed_skill_workflows.py -x</automated>
  </verify>
  <done>
    - rd-agent has workflows/intent-routing.md, workflows/start-contract.md, references/failure-routing.md
    - rd-agent SKILL.md no longer has Intent-first routing, Paused-run continuation, Minimum/Recommended start, Default stop, Failure handling, If information is missing
    - rd-agent SKILL.md has ## Internal workflows and ## References with conditional loads
    - rd-agent SKILL.md has strengthened ## When not to use lines
    - rd-tool-catalog SKILL.md has strengthened ## When not to use lines
    - test_phase20_rd_agent_skill_contract.py updated: 3 tests read from workflow/reference files, 1 test updated for removed section ordering
    - Gate 1: all tests pass
    - Gate 2: rd-agent workflows/ and references/ resolve in both runtimes
    - All 7 new workflow/reference files exist
    - All 6 SKILL.md files thinned with conditional loading
    - Blueprint v2 Waves 0-3 complete
  </done>
</task>

</tasks>

<verification>
After all 3 tasks complete:

1. Gate 1 final run (all existing tests):
   ```bash
   uv run pytest tests/test_phase18_skill_installation.py \
     tests/test_phase20_stage_skill_contracts.py \
     tests/test_phase20_rd_agent_skill_contract.py \
     tests/test_phase14_stage_skills.py \
     tests/test_phase14_skill_agent.py -x -v
   ```

2. Gate 2 final run (installed-skill smoke):
   ```bash
   uv run pytest tests/test_installed_skill_workflows.py -x -v
   ```

3. Structural verification:
   ```bash
   # All 7 new files exist
   ls skills/rd-propose/workflows/continue.md
   ls skills/rd-code/workflows/continue.md
   ls skills/rd-execute/workflows/continue.md
   ls skills/rd-evaluate/workflows/continue.md
   ls skills/rd-agent/workflows/intent-routing.md
   ls skills/rd-agent/workflows/start-contract.md
   ls skills/rd-agent/references/failure-routing.md

   # No SKILL.md has unconditional loading (progressive disclosure constraint)
   grep -l "^- Load " skills/*/SKILL.md | while read f; do
     grep "^- Load " "$f" | grep -v " when " && echo "FAIL: unconditional load in $f"
   done

   # Advisory line counts
   wc -l skills/*/SKILL.md
   ```
</verification>

<success_criteria>
- Gate 1 green: all existing pytest tests pass (37+ tests, 0 failures)
- Gate 2 green: installed skills resolve workflows/ and references/ in both runtimes
- 7 new workflow/reference files created with faithful content extraction
- 6 SKILL.md files thinned (4 stage skills + rd-agent + rd-tool-catalog)
- All conditional load instructions use "Load X when Y" format
- No unconditional loading in any SKILL.md
- rd-execute blocking_reasons written in full (not parameterized)
- rd-evaluate recommendation branching written in full (not parameterized)
</success_criteria>

<output>
After completion, create `.planning/quick/260323-wsb-blueprint-v2-skill-wave-0-3/260323-wsb-SUMMARY.md`
</output>
