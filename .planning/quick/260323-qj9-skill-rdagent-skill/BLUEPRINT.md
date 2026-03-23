# RDagent Skill Refactoring Blueprint

This blueprint converts the 260323-qfz skill-improvement analysis into a
concrete, line-by-line refactoring plan for the 6 RDagent skills. Every
extraction target names source lines and destination file. Every workflow
specifies scope boundaries. An executor can pick up any single wave and execute
it without re-reading the original analysis.

---

## Part 1: Target Architecture

After refactoring, each skill follows this directory structure:

```
skills/{skill-name}/
  SKILL.md              # thin adapter: trigger, boundary, execution context, output contract
  workflows/            # internal step-by-step pipeline (not public surface)
  references/           # long rules, checklists, routing tables
  assets/               # templates, skeletons (when needed)
```

A new shared directory holds deduplicated prose:

```
skills/_shared/
  references/
    stage-continuation-contract.md
    tool-catalog-routing.md
    stage-failure-handling.md
    skill-review-checklist.md
```

### Symlink structure

The canonical skill root is `skills/` at repo root. `.claude/skills/` contains
per-skill symlinks pointing to `skills/{name}`. Because the symlinks target
individual skill directories (not the `skills/` root), the new `skills/_shared/`
directory is NOT automatically visible through `.claude/skills/`. Two options:

1. **Add a symlink:** `.claude/skills/_shared -> skills/_shared` (recommended).
2. **Use repo-root-relative paths:** Each SKILL.md references `@skills/_shared/references/...` using the repo root, which Claude resolves regardless of which symlink entry point loaded the skill.

The recommended approach is option 1 for consistency. Add the symlink in Wave 0.

### Target line counts

| Skill | Current lines | Target SKILL.md | Extracted to |
|-------|--------------|-----------------|--------------|
| rd-agent | 155 | ~60 | 2 workflows, 2 references |
| rd-propose | 85 | ~40 | 3 shared references |
| rd-code | 85 | ~40 | 3 shared references |
| rd-execute | 88 | ~40 | 3 shared references |
| rd-evaluate | 87 | ~40 | 3 shared references |
| rd-tool-catalog | 67 | ~55 | none (already close) |

---

## Part 2: Extraction Map (per skill)

### rd-agent (155 lines -> target ~60 lines)

**Keep in SKILL.md (adapter surface):**

| Section | Current lines | Action |
|---------|--------------|--------|
| Frontmatter + description | 1-8 | Keep as-is |
| Tool execution context | 12-18 | Keep as-is |
| Trigger requests | 20-26 | Keep as-is |
| When to use | 28-35 | Keep as-is |
| Required fields | 64-71 | Keep as-is |
| Optional fields | 73-78 | Keep as-is |
| When to route to rd-tool-catalog | 113-119 | Keep as-is |
| When not to use | 121-125 | Keep, strengthen (see below) |
| Output | 141-149 | Keep as-is |
| Success contract | 151-155 | Keep as-is |

**Extract to `workflows/intent-routing.md`:**

| Source | Current lines | Content |
|--------|--------------|---------|
| Intent-first routing | 37-52 | State inspection logic, paused-run detection, routing reply format (4+2 fields), preflight-blocks-recommended-path rule, operator-facing conciseness rule |
| Paused-run continuation preference | 54-63 | run_id/branch_id/stage surfacing, stage-to-skill mapping, preflight-fail handling, new-run-as-fallback rule, detail_hint vs next_step_detail selection |

Scope boundary for `workflows/intent-routing.md`:
- **Owns:** state inspection, paused-run detection, routing reply format, preflight gate interaction, detail_hint vs next_step_detail selection
- **Does NOT own:** stage-level continuation details, tool selection, start payload validation

**Extract to `workflows/start-contract.md`:**

| Source | Current lines | Content |
|--------|--------------|---------|
| Minimum start contract | 79-84 | Strict minimum fields, first-step payload explanation, fresh-start path |
| Recommended multi-branch contract | 86-103 | Skill-first progression, optional control fields, branch_hypotheses, example payload shape |
| Default stop behavior | 105-112 | gated + max_stage_iterations=1, awaiting_operator, human review pause, continuous unattended alternative |

Scope boundary for `workflows/start-contract.md`:
- **Owns:** minimum vs recommended payload definition, example shape, field validation order, stop behavior after start, execution mode semantics
- **Does NOT own:** stage execution, branch lifecycle, intent routing

**Extract to `references/stop-behavior.md`:**

Merged into `workflows/start-contract.md` instead of a separate file. The stop
behavior (lines 105-112) is tightly coupled to the start contract (it defines
what happens after the start payload is accepted). Keeping them together avoids
a 7-line orphan reference.

**Extract to `references/failure-routing.md`:**

| Source | Current lines | Content |
|--------|--------------|---------|
| Failure handling | 127-132 | Missing inputs -> inspect state -> surface missing -> ask operator; stage-specific -> route to stage skill; inspection-only -> rd-tool-catalog |
| If information is missing | 134-139 | Inspect before asking, surface exact missing values, only ask for underivable values, route stage-specific tasks to stage skill |

Scope boundary for `references/failure-routing.md`:
- **Owns:** missing-field inspection protocol, state-first recovery, route-to-correct-stage logic, rd-tool-catalog escalation decision
- **Does NOT own:** stage-level failure handling (that belongs in shared reference), start contract validation

**Strengthen in SKILL.md (do not extract):**

Add to `When not to use` section as fixed-format lines:
```
- If blocked, route to: the corresponding stage skill (rd-propose, rd-code, rd-execute, rd-evaluate) or rd-tool-catalog for inspection-only tasks.
- If state absent, fresh-start only: do not search other repos or HOME; stay on the minimum start contract path.
```

**SKILL.md after extraction references:**
```
## Internal workflows
- Load `workflows/intent-routing.md` when processing plain-language intent or paused-run detection.
- Load `workflows/start-contract.md` when the operator needs the start payload or stop behavior.

## References
- Load `references/failure-routing.md` when handling missing inputs or routing failures.
```

### rd-propose (85 lines -> target ~40 lines)

**Keep in SKILL.md:**

| Section | Current lines | Action |
|---------|--------------|--------|
| Frontmatter + description | 1-8 | Keep as-is |
| Tool execution context | 12-17 | Keep as-is |
| Trigger requests | 19-23 | Keep as-is |
| When to use | 25-29 | Keep as-is |
| When not to use | 59-63 | Keep, strengthen |
| Output | 71-72 | Keep as-is |
| Outcome guide | 74-79 | Keep as-is |
| Success contract | 81-85 | Keep as-is |

**Extract to shared `_shared/references/stage-continuation-contract.md`:**

| Source | Current lines | Content |
|--------|--------------|---------|
| Continue contract | 31-36 | "continue a paused run inside one known step" pattern |
| Required fields | 38-43 | run_id, branch_id, summary, artifact_ids |
| If information is missing | 45-50 | inspect state -> surface missing -> ask operator -> rd-tool-catalog escalation |

These sections are nearly identical across rd-propose, rd-code, rd-execute, rd-evaluate. See Part 3 for parameterization.

**Extract to shared `_shared/references/tool-catalog-routing.md`:**

| Source | Current lines | Content |
|--------|--------------|---------|
| When to route to rd-tool-catalog | 52-57 | Agent-side routing for direct inspection, CLI primitive, keep operator on stage path |

Identical pattern across all four stage skills.

**Extract to shared `_shared/references/stage-failure-handling.md`:**

| Source | Current lines | Content |
|--------|--------------|---------|
| Failure handling | 65-69 | Missing fields -> inspect state -> surface missing -> rd-tool-catalog escalation -> wrong stage routing |

Same pattern across all four stage skills, with stage-specific override for rd-execute.

**Strengthen in SKILL.md:**

Add fixed-format lines to `When not to use`:
```
- If blocked, route to: rd-agent for full-loop restart, or the correct stage skill if the branch is in another stage.
- If state absent, fresh-start only: do not fabricate continuation context; route to rd-agent for the minimum start contract.
```

**SKILL.md after extraction references:**
```
## Shared references
- Load `@skills/_shared/references/stage-continuation-contract.md` when continuing a paused framing step (stage=framing, next_skill=rd-code).
- Load `@skills/_shared/references/tool-catalog-routing.md` when deciding whether to drop to a direct tool.
- Load `@skills/_shared/references/stage-failure-handling.md` when handling missing fields or wrong-stage routing.
```

### rd-code (85 lines -> target ~40 lines)

Identical extraction pattern to rd-propose. Differences only in parameterization:

| Parameter | rd-propose value | rd-code value |
|-----------|-----------------|---------------|
| `stage_name` | framing | build |
| `next_skill` | rd-code | rd-execute |
| `extra_fields` | (none) | (none) |

**Keep, extract, and strengthen:** Same sections as rd-propose above, with `framing` replaced by `build` and `rd-code` replaced by `rd-execute` in the continuation contract.

### rd-execute (88 lines -> target ~40 lines)

Identical extraction pattern to rd-propose. Key difference: rd-execute has one extra required field.

| Parameter | rd-execute value |
|-----------|-----------------|
| `stage_name` | verify |
| `next_skill` | rd-evaluate |
| `extra_fields` | `blocking_reasons` (for blocked verification path) |

The `blocking_reasons` field (line 44 in rd-execute) and the additional failure handling for blocked path (line 68-69) are stage-specific overrides that the shared reference must accommodate via the parameterization table.

### rd-evaluate (87 lines -> target ~40 lines)

Identical extraction pattern to rd-propose. Key difference: rd-evaluate has one extra required field and a branching outcome.

| Parameter | rd-evaluate value |
|-----------|------------------|
| `stage_name` | synthesize |
| `next_skill` | rd-propose (if continue) or none (if stop) |
| `extra_fields` | `recommendation` (continue / stop) |

The `recommendation` field (line 43 in rd-evaluate) and the branching next-skill logic are stage-specific overrides.

### rd-tool-catalog (67 lines -> target ~55 lines, already close)

**No extraction needed.** Already has `references/tool-selection.md` and is the leanest skill.

**Minor additions:**

1. Add fixed-format routing lines to `When not to use`:
```
- If blocked, route to: rd-agent for orchestration, or the correct stage skill if the caller knows which stage they need.
- If state absent: this skill does not require persisted V3 state to function; it operates on catalog metadata only.
```

2. Verify `Failure handling` section covers the "route back out" cases explicitly (it already does at lines 49-52).

---

## Part 3: Internal Workflows and Shared References to Create

### 1. `skills/rd-agent/workflows/intent-routing.md`

**Source:** rd-agent SKILL.md lines 37-63

**Scope boundary:**
- **Owns:** state inspection, paused-run detection, routing reply format (current_state / routing_reason / exact_next_action / recommended_next_skill), optional detail fields (next_step_detail / detail_hint), preflight gate interaction, stage-to-skill continuation mapping
- **Does NOT own:** stage-level continuation details (those live in stage-continuation-contract.md), tool selection (that lives in rd-tool-catalog), start payload validation (that lives in start-contract.md)

**Content outline:**
1. Intent inspection protocol: inspect persisted state before routing
2. Paused-run detection: surface run_id, branch_id, stage; map stage to skill
3. Routing reply format: the 4+2 field structure
4. Preflight-blocked handling: keep recommended_next_skill visible, add blocker + repair
5. Fresh-start fallback: when no paused work dominates context
6. Detail selection: detail_hint for healthy routes, next_step_detail for blocked/fresh

### 2. `skills/rd-agent/workflows/start-contract.md`

**Source:** rd-agent SKILL.md lines 79-112

**Scope boundary:**
- **Owns:** minimum start contract (5 required fields), recommended multi-branch contract (+ optional fields), example payload shape, field validation order, default stop behavior (gated + max_stage_iterations=1), execution mode semantics
- **Does NOT own:** stage execution, branch lifecycle, intent routing, failure recovery

**Content outline:**
1. Minimum start contract: title, task_summary, scenario_label, stage_inputs.framing.summary, stage_inputs.framing.artifact_ids
2. Recommended multi-branch contract: minimum + initial_branch_label, execution_mode, max_stage_iterations, branch_hypotheses
3. Example payload shape (the existing text block)
4. Default stop behavior: gated + max_stage_iterations=1, awaiting_operator semantics
5. Continuous unattended path: when and how to change the default safety boundary

### 3. `skills/_shared/references/stage-continuation-contract.md`

**Source:** Deduplicated from rd-propose (31-50), rd-code (31-50), rd-execute (31-51), rd-evaluate (31-51)

**Scope boundary:**
- **Owns:** shared continuation fields (run_id, branch_id, summary, artifact_ids), continue-contract semantics, missing-field recovery protocol, rd-tool-catalog escalation protocol
- **Does NOT own:** stage-specific extra fields (those stay in individual SKILL.md), stage transition rules, outcome guides

**Parameterization table:**

| Parameter | rd-propose | rd-code | rd-execute | rd-evaluate |
|-----------|-----------|---------|------------|-------------|
| `{stage_name}` | framing | build | verify | synthesize |
| `{next_skill}` | rd-code | rd-execute | rd-evaluate | rd-propose (continue) / none (stop) |
| `{stage_verb}` | framing | build | verify / block | synthesize / close |
| `{extra_fields}` | (none) | (none) | blocking_reasons | recommendation (continue/stop) |

**Content outline:**
1. Continue contract: "continue a paused run inside one known `{stage_name}` step"
2. Core required fields: run_id, branch_id, summary, artifact_ids (universal)
3. Stage-specific extra fields: reference the parameterization table
4. Missing-field recovery protocol:
   - Inspect current run/branch state first
   - Surface exact missing values with field names
   - Ask operator only for underivable values
   - rd-tool-catalog as agent-side escalation path
5. Return-with-resolved-payload expectation

### 4. `skills/_shared/references/tool-catalog-routing.md`

**Source:** Deduplicated from rd-propose (52-57), rd-code (52-57), rd-execute (53-58), rd-evaluate (53-58)

**Scope boundary:**
- **Owns:** when to downshift from any stage skill to rd-tool-catalog, "keep operator on stage path" rule, direct-tool execution root constraint
- **Does NOT own:** tool selection logic (that lives in rd-tool-catalog's own references), stage transition decisions, rd-agent-level routing

**Content outline:**
1. When to route: agent-side need for direct inspection, CLI primitive, or recovery state
2. Execution root constraint: keep direct-tool calls in same standalone V3 repo root
3. Operator-path rule: route to rd-tool-catalog but keep operator on the stage skill path
4. When NOT to route: high-level skill boundary is sufficient

### 5. `skills/_shared/references/stage-failure-handling.md`

**Source:** Deduplicated from rd-propose (65-69), rd-code (65-69), rd-execute (65-71), rd-evaluate (65-69)

**Scope boundary:**
- **Owns:** missing-field inspection protocol (stage level), state-first recovery, route-to-correct-stage logic, rd-tool-catalog escalation decision
- **Does NOT own:** rd-agent-level failure routing (that has its own reference), start-contract validation, tool selection

**Parameterization table (stage-specific overrides):**

| Parameter | rd-propose | rd-code | rd-execute | rd-evaluate |
|-----------|-----------|---------|------------|-------------|
| `{missing_fields}` | run_id, branch_id, summary, artifact_ids | same | same + blocking_reasons | same + recommendation |
| `{wrong_stage_action}` | route to correct stage or rd-agent | same | same | same |
| `{extra_failure_path}` | (none) | (none) | "If blocked path required but blocking_reasons unresolved, ask only for blocking reasons that cannot be derived from current verification state" | (none) |

**Content outline:**
1. Missing fields: inspect state -> surface exact missing values -> ask only for unresolvable
2. Stage-specific extra field handling (parameterized)
3. Inspection/primitive fallback: rd-tool-catalog as agent-side escalation
4. Wrong-stage detection: route to correct stage skill or rd-agent

### 6. `skills/_shared/references/skill-review-checklist.md`

Not extracted from any existing skill. Created new as a standalone audit tool. See Part 4.

---

## Part 4: Skill Review Checklist

Create at `skills/_shared/references/skill-review-checklist.md`.

This checklist is designed to be mechanically verifiable (grep, wc, structural
inspection) rather than subjective. Run it after each refactoring step.

### Adapter shape (SKILL.md)

- [ ] SKILL.md is under 80 lines (`wc -l`)
- [ ] Has YAML frontmatter with `name` and `description`
- [ ] Has `## Tool execution context` section
- [ ] Has `## Trigger requests` section with at least 3 examples
- [ ] Has `## When to use` section
- [ ] Has `## When not to use` section with at least 2 items
- [ ] Has `"If blocked, route to:"` as a fixed-format line in When not to use
- [ ] Has `"If state absent"` behavior documented (either in When not to use or a dedicated line)
- [ ] Has `## Output` section describing what the skill returns
- [ ] Has `## Success contract` section with concrete pass criteria

### Failure and routing

- [ ] Has a failure path (not just the happy path) -- either inline or via `@references/`
- [ ] Has explicit routing targets (named skills, not "the appropriate skill")
- [ ] Does NOT contain step-by-step pipeline logic (>5 numbered/ordered steps belong in `workflows/`)
- [ ] Does NOT contain decision trees with >3 branches (those belong in `references/`)

### Deduplication

- [ ] Does NOT duplicate text that exists identically in another skill's SKILL.md
- [ ] Shared patterns reference `@skills/_shared/references/` instead of inlining
- [ ] Stage-specific overrides are parameterized, not copy-pasted

### Progressive disclosure

- [ ] References use "Load X only when Y" language (conditional loading)
- [ ] SKILL.md does not unconditionally load all references at the top
- [ ] Workflow files are loaded only when the agent reaches that execution step

### Structural verification commands

```bash
# Line count check (must be < 80)
wc -l skills/*/SKILL.md

# Required sections check
for skill in rd-agent rd-propose rd-code rd-execute rd-evaluate rd-tool-catalog; do
  echo "=== $skill ==="
  grep -c "## Tool execution context"    "skills/$skill/SKILL.md"
  grep -c "## When to use"               "skills/$skill/SKILL.md"
  grep -c "## When not to use"           "skills/$skill/SKILL.md"
  grep -c "## Output"                    "skills/$skill/SKILL.md"
  grep -c "## Success contract"          "skills/$skill/SKILL.md"
  grep -c "If blocked, route to"         "skills/$skill/SKILL.md"
done

# Duplication check (find identical multi-line blocks across skills)
# Compare each pair of stage skills for identical paragraphs
for a in rd-propose rd-code rd-execute rd-evaluate; do
  for b in rd-propose rd-code rd-execute rd-evaluate; do
    if [ "$a" \< "$b" ]; then
      comm -12 \
        <(sed 's/framing\|build\|verify\|synthesize/{stage}/g' "skills/$a/SKILL.md" | sort -u) \
        <(sed 's/framing\|build\|verify\|synthesize/{stage}/g' "skills/$b/SKILL.md" | sort -u) \
      | wc -l | xargs -I{} echo "$a vs $b: {} shared lines (after stage-name normalization)"
    fi
  done
done

# Shared reference existence check
for ref in stage-continuation-contract.md tool-catalog-routing.md stage-failure-handling.md skill-review-checklist.md; do
  test -f "skills/_shared/references/$ref" && echo "FOUND: $ref" || echo "MISSING: $ref"
done
```

---

## Part 5: Execution Order

### Wave 0: Infrastructure (no dependencies)

| Step | Action | Files created |
|------|--------|--------------|
| 0.1 | Create `skills/_shared/references/` directory | directory only |
| 0.2 | Create `skills/rd-agent/workflows/` directory | directory only |
| 0.3 | Create `skills/rd-agent/references/` directory | directory only |
| 0.4 | Add symlink `.claude/skills/_shared -> skills/_shared` | symlink |
| 0.5 | Create `skills/_shared/references/skill-review-checklist.md` | Part 4 content |

**Verification:** All directories exist, symlink resolves, checklist file is readable from `.claude/skills/_shared/references/`.

### Wave 1: Shared reference extraction (no skill depends on these yet)

| Step | Action | Source | Destination |
|------|--------|--------|-------------|
| 1.1 | Extract and parameterize stage continuation contract | rd-propose 31-50, rd-code 31-50, rd-execute 31-51, rd-evaluate 31-51 | `skills/_shared/references/stage-continuation-contract.md` |
| 1.2 | Extract and deduplicate tool-catalog routing | rd-propose 52-57, rd-code 52-57, rd-execute 53-58, rd-evaluate 53-58 | `skills/_shared/references/tool-catalog-routing.md` |
| 1.3 | Extract and parameterize stage failure handling | rd-propose 65-69, rd-code 65-69, rd-execute 65-71, rd-evaluate 65-69 | `skills/_shared/references/stage-failure-handling.md` |

**Verification:** Each shared reference file exists, contains the parameterization table, and is loadable via `@skills/_shared/references/{name}`.

### Wave 2: Stage skill thinning (depends on Wave 1)

Can execute all four in parallel since they have no inter-dependencies.

| Step | Skill | Actions |
|------|-------|---------|
| 2.1 | rd-propose | Remove Continue contract (31-36), Required fields (38-43), If information missing (45-50), When to route to rd-tool-catalog (52-57), Failure handling (65-69). Add shared reference load lines. Add "If blocked, route to" and "If state absent" to When not to use. |
| 2.2 | rd-code | Same extraction pattern as 2.1, with build/rd-execute substitutions. |
| 2.3 | rd-execute | Same pattern as 2.1, plus keep `blocking_reasons` as a stage-specific extra field note in SKILL.md (1 line). Remove the extra failure handling prose for blocking_reasons (use shared ref parameterization). |
| 2.4 | rd-evaluate | Same pattern as 2.1, plus keep `recommendation` as a stage-specific extra field note in SKILL.md (1 line). |

**Per-skill post-step verification:** Run skill-review checklist from Part 4. Must pass all items.

### Wave 3: rd-agent thinning (depends on Wave 2 proving the pattern)

| Step | Action | Source lines | Destination |
|------|--------|-------------|-------------|
| 3.1 | Extract intent-routing workflow | 37-63 | `skills/rd-agent/workflows/intent-routing.md` |
| 3.2 | Extract start-contract workflow (includes stop behavior) | 79-112 | `skills/rd-agent/workflows/start-contract.md` |
| 3.3 | Extract failure-routing reference | 127-139 | `skills/rd-agent/references/failure-routing.md` |
| 3.4 | Thin rd-agent SKILL.md: remove extracted sections, add workflow/reference load lines, add "If blocked, route to" and "If state absent" to When not to use |
| 3.5 | Run skill-review checklist against rd-agent |

**Verification:** rd-agent SKILL.md under 60 lines, all extracted files exist, checklist passes.

### Wave 4: rd-tool-catalog polish (depends on nothing, can run parallel with Wave 2/3)

| Step | Action |
|------|--------|
| 4.1 | Add "If blocked, route to" fixed-format line to When not to use |
| 4.2 | Add "If state absent" note (catalog does not require V3 state) |
| 4.3 | Run skill-review checklist |

**Verification:** Checklist passes. No extraction needed.

### Wave 5: Cross-skill verification (depends on all previous waves)

| Step | Verification action |
|------|-------------------|
| 5.1 | Run `wc -l skills/*/SKILL.md` -- no skill exceeds 80 lines |
| 5.2 | Run duplication check from Part 4 -- no identical prose across stage skills (after stage-name normalization) |
| 5.3 | Verify all shared references are loadable from each skill directory via relative path |
| 5.4 | Verify `.claude/skills/_shared/references/` symlink resolves correctly |
| 5.5 | Run full skill-review checklist against all 6 skills |
| 5.6 | Verify progressive disclosure: no SKILL.md unconditionally loads all references at the top |

---

## Part 6: Risk Notes

### Symlink behavior with `_shared/`

The existing symlink structure is:
```
.claude/skills/rd-agent     -> skills/rd-agent
.claude/skills/rd-code      -> skills/rd-code
.claude/skills/rd-evaluate  -> skills/rd-evaluate
.claude/skills/rd-execute   -> skills/rd-execute
.claude/skills/rd-propose   -> skills/rd-propose
.claude/skills/rd-tool-catalog -> skills/rd-tool-catalog
```

Adding `skills/_shared/` means:
- Claude loading skills via `.claude/skills/` will NOT automatically see `_shared/` unless a symlink is added (Wave 0 step 0.4).
- Relative paths in SKILL.md like `@../references/...` would resolve differently depending on whether the skill is loaded from `skills/rd-agent/SKILL.md` or `.claude/skills/rd-agent/SKILL.md` (the symlink target is the same file, but the `..` resolves differently in each context).
- **Mitigation:** Use `@skills/_shared/references/...` (repo-root-relative) in all SKILL.md reference lines, not `../_shared/references/...`. Claude resolves repo-root-relative `@` paths regardless of which symlink entry point was used.

### Backward compatibility

Existing Claude sessions that have cached SKILL.md content in their context
window will not see refactored versions until a fresh session. No migration
action is needed, but refactored skills will diverge from cached versions in
active sessions.

**Mitigation:** None required. The refactoring is purely a structural
reorganization; no behavioral contract changes. The thin SKILL.md will still
contain the same boundary declarations, just without the internal pipeline
detail that was always informational rather than contractual.

### Progressive disclosure is the key constraint

The entire refactoring is pointless if the new SKILL.md files just add
`@references/` loads at the top that unconditionally pull everything in. The
critical constraint is:

- SKILL.md uses conditional loading: "Load X only when Y"
- Workflow files are loaded only when the agent reaches that execution step
- References are loaded only when the agent needs that specific decision tree

If this constraint is violated, the refactoring merely moves text around
without reducing the context burden. Every executor must verify this with the
checklist item: "Does NOT unconditionally load all references at the top."

### Parameterization vs templating

The shared references use a parameterization table (stage_name, next_skill,
extra_fields) rather than literal `{stage_name}` template variables in the
prose. The expectation is that each SKILL.md's reference-load line specifies
the stage parameters:

```
Load @skills/_shared/references/stage-continuation-contract.md
when continuing a paused framing step (stage=framing, next_skill=rd-code).
```

The shared reference contains the parameterization table so the agent can
resolve the correct values for the current stage. This is simpler and more
robust than literal template substitution, which Claude does not natively
support in `@` references.

### Execution risk ordering

The wave ordering is intentional for risk management:
1. **Wave 1 (shared refs)** is lowest risk -- creates new files without modifying existing skills.
2. **Wave 2 (stage skills)** is moderate risk -- modifies 4 skills but they follow an identical pattern, so the first one (rd-propose) proves the approach and the remaining 3 are mechanical.
3. **Wave 3 (rd-agent)** is highest risk -- largest skill with the most unique content. By this point, the shared reference pattern is proven and the stage skills demonstrate the thin-adapter shape.
4. **Wave 4 (rd-tool-catalog)** is trivial -- minor additions only.
5. **Wave 5 (verification)** catches any regressions.

If any wave fails its verification, STOP and fix before proceeding to the next
wave. Do not batch-apply waves hoping verification passes at the end.
