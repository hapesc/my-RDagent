# Phase 25: Fix QA-discovered operator guidance and multi-branch UX gaps - Research

**Researched:** 2026-03-23
**Domain:** V3 operator guidance contracts, multi-branch UX exposure, stage state materialization
**Confidence:** HIGH

## Summary

Phase 25 addresses 6 QA-discovered issues in the V3 pipeline and promotes multi-branch
exploration from a hidden power-user feature to the default UX. The codebase is mature
(163 passing tests, well-factored contracts), and the changes are surgical: every
modification targets an existing file with a clear before/after contract. No new
libraries, frameworks, or external dependencies are needed.

The primary risk is the `disposition` -> `recovery_assessment` rename, which touches
~18 files and 3 Pydantic models with `extra="forbid"` and `frozen=True` constraints.
A single missed rename will cause a runtime Pydantic validation error. The second
risk is ensuring backward compatibility in the `structuredContent` output shape for
any consumers that read `decision.disposition` from existing persisted state.

**Primary recommendation:** Execute as 4 sequential waves: (1) commit existing Phase 24
uncommitted fixes, (2) guidance completeness + outcome consistency, (3) disposition
rename, (4) multi-branch UX + stage materialization. Each wave is independently
testable and reversible.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `execution_mode` default changes from `gated` to `exploration` for new runs.
- `exploration_mode` and `branch_hypotheses` must be exposed in the `rd_run_start` input schema and tool catalog description.
- `route_user_intent` must recommend multi-branch exploration in its `start_new_run` guidance, including auto-generated branch hypotheses in `next_step_detail`.
- When routing detects a research-type intent, the system should auto-generate 2-3 branch hypotheses (e.g., "ResNet18 transfer", "EfficientNet-B0", "Simple CNN baseline") and present them in the guidance for user confirmation or modification.
- Users can still explicitly request `gated` mode for single-branch work.
- Abandon the Phase 24 `selective-detail` / `detail_hint` pattern.
- Every operator guidance response -- completed, blocked, reused, replay, review, new-run -- must include a `next_step_detail` field with a copy-pasteable parameter skeleton for the recommended next skill.
- The `detail_hint` field ("If you want, I can expand...") is removed; the skeleton is always present.
- When a stage entry completes successfully, it must automatically create a NOT_STARTED snapshot for the next stage and update `branch.current_stage_key` to the next stage key.
- Add a consistent `outcome` field to `structuredContent` for all 4 stage entries (rd_propose, rd_code, rd_execute, rd_evaluate).
- Valid outcome values: `completed`, `blocked`, `preflight_blocked`, `reused`, `replay`, `review`.
- Rename `decision.disposition` to `decision.recovery_assessment` across all stage entries and the `ResumeDecision` model.
- `operator_guidance` continues to reflect post-execution results; `decision.recovery_assessment` continues to reflect the entry-time recovery state.
- Uncommitted Phase 24 fixes must be committed as the first step.

### Claude's Discretion
- Exact wording of auto-generated branch hypotheses.
- Whether `detail_hint` field is removed from `OperatorGuidance` contract or kept as deprecated/unused.
- Implementation order of the 6 fixes within Phase 25.

### Deferred Ideas (OUT OF SCOPE)
- Phase 26: Adaptive DAG Path Management (SelectParents, pruning, first-layer diversity)
- Phase 27: Cross-branch Communication + Multi-trace Merge (global best injection, probabilistic sampling, component synthesis)
- Phase 28: Aggregated Validation and Holdout Calibration (holdout set, standardized ranking, overfitting prevention)
</user_constraints>

<phase_requirements>
## Phase Requirements

Phase 25 is a QA-fix phase with no new formal requirement IDs. The 6 issues map to the
success criteria defined in the ROADMAP:

| ID | Description | Research Support |
|----|-------------|-----------------|
| SC-1 | route_user_intent start_new_run guidance includes auto-generated branch hypotheses and recommends multi-branch exploration by default | Multi-branch UX section: `build_start_new_run_guidance` rewrite, hypothesis generation helper, `RunStartRequest` schema extension |
| SC-2 | rd_run_start schema exposes exploration_mode and branch_hypotheses | Tool catalog section: `RunStartRequest` field additions, `rd_run_start` _ToolSpec example update |
| SC-3 | All stage entry guidance paths include a copy-pasteable next_step_detail skeleton | Guidance completeness section: `build_stage_guidance_response` always passes `next_step_detail`, `_minimum_continuation_skeleton` used everywhere |
| SC-4 | Stage completion materializes a NOT_STARTED next-stage snapshot and updates branch.current_stage_key | Stage materialization section: `StageTransitionService.publish_stage_complete` extension |
| SC-5 | All 4 stage entries expose a consistent outcome field in structuredContent | Outcome consistency section: audit of missing outcome fields in rd_propose, rd_code, rd_evaluate |
| SC-6 | decision.disposition renamed to decision.recovery_assessment across all surfaces | Disposition rename section: 18-file rename map with Pydantic model changes |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2,<3 | All V3 contracts use frozen Pydantic models with `extra="forbid"` | Already the project's single data-modeling dependency |
| pytest | >=7.4.0 | Test runner for 163 existing tests | Already configured in pyproject.toml |

### Supporting
No new dependencies needed. Phase 25 is a pure refactor/fix phase using existing code.

## Architecture Patterns

### Current Source File Map (files to modify)

```
v3/
  contracts/
    operator_guidance.py    # OperatorGuidance model (remove detail_hint)
    recovery.py             # RecoveryAssessment.disposition rename
    run.py                  # ExecutionMode enum (leave as-is, default change happens in entry)
    tool_io.py              # RunStartRequest (add exploration_mode, branch_hypotheses)
    exploration.py          # ExplorationMode enum (already exists, reuse)
  entry/
    rd_agent.py             # route_user_intent + rd_agent (multi-branch default, hypothesis gen)
    rd_propose.py           # outcome field, recovery_assessment rename, next_step_detail, materialization
    rd_code.py              # same
    rd_execute.py           # outcome already exists, recovery_assessment rename, next_step_detail, materialization
    rd_evaluate.py          # outcome field, recovery_assessment rename, next_step_detail
    tool_catalog.py         # rd_run_start spec (expose exploration_mode, branch_hypotheses)
  orchestration/
    operator_guidance.py    # Remove detail_hint, always populate next_step_detail
    resume_planner.py       # ResumeDecision.disposition -> recovery_assessment
    stage_transition_service.py  # Add next-stage NOT_STARTED materialization
    recovery_service.py     # RecoveryAssessment.disposition used in _disposition_for
    scoring_service.py      # recovery.disposition reference
    selection_service.py    # recovery.disposition reference
    skill_loop_service.py   # decision["disposition"] reference
```

### Pattern 1: Consistent outcome field in structuredContent

**What:** Every stage entry response must include `"outcome": <value>` at the top level
of `structuredContent`, alongside `owned_stage`, `operator_guidance`, `decision`, etc.

**Current state by file:**

| File | preflight_blocked | reused | review | replay | completed | blocked |
|------|:-:|:-:|:-:|:-:|:-:|:-:|
| rd_propose.py | HAS outcome | MISSING | MISSING | MISSING | MISSING | n/a |
| rd_code.py | HAS outcome | MISSING | MISSING | MISSING | MISSING | n/a |
| rd_execute.py | HAS outcome | HAS | HAS | HAS | HAS | HAS |
| rd_evaluate.py | HAS outcome | MISSING | MISSING | MISSING | MISSING | n/a |

**Fix:** Add `"outcome": "<value>"` to every `_tool_response` call's structuredContent dict
in rd_propose, rd_code, and rd_evaluate. rd_execute already has full coverage and serves
as the reference pattern.

### Pattern 2: Copy-pasteable next_step_detail on every path

**What:** Abandon `detail_hint`. Every guidance response includes a `next_step_detail`
with a runnable skeleton like:
```
rd-code run_id="run-001" branch_id="branch-001" summary="..." artifact_ids=[...]
```

**Current state:**
- `build_start_new_run_guidance` -- already populates `next_step_detail` via `_minimum_start_skeleton`
- `build_paused_run_guidance` -- blocked path populates `next_step_detail`, executable path uses `detail_hint` instead
- `build_stage_guidance_response` -- accepts `next_step_detail` as optional param, most callers don't pass it
- Stage entries (rd_propose, rd_code, rd_execute, rd_evaluate) -- none of the disposition branches (completed, reused, replay, review) pass `next_step_detail`

**Fix:** Use `_minimum_continuation_skeleton(run_id, branch_id)` in every
`build_stage_guidance_response` call. The skeleton format is already defined:
```python
f'run_id="{run_id}" branch_id="{branch_id}" summary="Summarize the current step." artifact_ids=["artifact-001"]'
```

For `build_paused_run_guidance` executable path: replace `detail_hint` with `next_step_detail`.

### Pattern 3: Next-stage NOT_STARTED materialization

**What:** When a stage completes successfully, auto-create a NOT_STARTED snapshot for
the next stage and update `branch.current_stage_key`.

**Current flow (no materialization):**
1. Entry calls `rd_stage_complete(StageCompleteRequest(... next_stage_key=NEXT))`
2. `rd_stage_complete` creates a `StageSnapshot(status=COMPLETED, next_stage_key=NEXT)`
3. `_publish` calls `service.publish_stage_complete(branch_id, snapshot)`
4. `StageTransitionService._publish_stage_snapshot` updates branch with `current_stage_key=snapshot.stage_key` (the COMPLETED stage, not the next one)

**The gap:** `current_stage_key` is set to the completed stage's key, not the next
stage's key. And no NOT_STARTED snapshot exists for the next stage.

**Fix location:** `StageTransitionService.publish_stage_complete` -- after publishing the
completed stage, if `stage_snapshot.next_stage_key` is not None, create and persist a
NOT_STARTED snapshot and advance `current_stage_key` to the next stage.

**Implementation:**
```python
def publish_stage_complete(self, branch_id: str, stage_snapshot: StageSnapshot) -> BranchSnapshot:
    branch = self._publish_stage_snapshot(
        branch_id,
        stage_snapshot.model_copy(update={"status": StageStatus.COMPLETED}),
    )
    if stage_snapshot.next_stage_key is not None:
        next_stage = StageSnapshot(
            stage_key=stage_snapshot.next_stage_key,
            stage_iteration=1,
            status=StageStatus.NOT_STARTED,
            summary="Prepared and requires preflight before execution.",
            artifact_ids=[],
        )
        branch = self._publish_stage_snapshot(branch_id, next_stage)
    return branch
```

This naturally sets `current_stage_key` to the next stage because
`_publish_stage_snapshot` always sets `current_stage_key = stage_snapshot.stage_key`.

### Pattern 4: disposition -> recovery_assessment rename

**What:** Rename the field `disposition` to `recovery_assessment` on:
1. `RecoveryAssessment` model (contracts/recovery.py)
2. `ResumeDecision` model (orchestration/resume_planner.py)
3. All downstream references

**Rename map (exhaustive):**

| File | Line(s) | Change |
|------|---------|--------|
| v3/contracts/recovery.py:50 | `disposition: RecoveryDisposition` | -> `recovery_assessment: RecoveryDisposition` |
| v3/orchestration/resume_planner.py:18 | `disposition: RecoveryDisposition` | -> `recovery_assessment: RecoveryDisposition` |
| v3/orchestration/resume_planner.py:39,57,75,92,110,123,131,145 | `disposition=...` | -> `recovery_assessment=...` |
| v3/orchestration/recovery_service.py:96,97,103 | `disposition = ...` / `disposition=disposition` | -> `recovery_assessment = ...` |
| v3/orchestration/recovery_service.py:124-137 | `_disposition_for` method | rename return var, keep method name (internal) |
| v3/orchestration/recovery_service.py:139-147 | `_recommended_next_step(stage, disposition)` | param rename |
| v3/orchestration/scoring_service.py:39-60 | `recovery.disposition` | -> `recovery.recovery_assessment` |
| v3/orchestration/selection_service.py:63 | `recovery.disposition` | -> `recovery.recovery_assessment` |
| v3/orchestration/skill_loop_service.py:101 | `decision["disposition"]` | -> `decision["recovery_assessment"]` |
| v3/entry/rd_propose.py:125,151,177 | `decision.disposition` | -> `decision.recovery_assessment` |
| v3/entry/rd_code.py:126,152,178 | `decision.disposition` | -> `decision.recovery_assessment` |
| v3/entry/rd_execute.py:128,155,182 | `decision.disposition` | -> `decision.recovery_assessment` |
| v3/entry/rd_evaluate.py:127,160,187 | `decision.disposition` | -> `decision.recovery_assessment` |
| v3/tools/recovery_tools.py:28 | `assessment.disposition.value` | -> `assessment.recovery_assessment.value` |
| tests/test_phase13_v3_tools.py:311,323,435 | `disposition=...` / `["disposition"]` | -> `recovery_assessment=...` / `["recovery_assessment"]` |
| tests/test_phase14_resume_and_reuse.py:123,131,144,152,165,196,227 | `decision.disposition` / `["disposition"]` | -> field rename |
| tests/test_phase16_selection.py:46,51-53 | `disposition=...` param | -> `recovery_assessment=...` |
| tests/test_phase24_stage_next_step_guidance.py:345 | `disposition=RecoveryDisposition.REUSE` | -> `recovery_assessment=...` |

**Critical risk:** Pydantic `extra="forbid"` means any JSON with the old field name
`disposition` will fail validation. Persisted state files on disk with `disposition`
will break on deserialization. This is acceptable since Phase 25 is a dev-facing fix
phase and no production persistence exists.

### Pattern 5: Multi-branch UX as default

**What:** Make exploration the natural starting path.

**Changes:**
1. `rd_agent.py:239` -- `execution_mode: ExecutionMode = ExecutionMode.GATED` changes default.
   However, `ExecutionMode` is `GATED | UNATTENDED` (not EXPLORATION). The context says
   "change default to exploration" which means using `ExplorationMode.EXPLORATION` as
   a separate parameter, not changing the ExecutionMode enum.

2. `RunStartRequest` in tool_io.py -- add two optional fields:
   ```python
   exploration_mode: ExplorationMode | None = ExplorationMode.EXPLORATION
   branch_hypotheses: list[str] | None = None
   ```

3. `route_user_intent` start_new_run path -- `build_start_new_run_guidance` must:
   - Generate 2-3 branch hypotheses from the user intent
   - Include them in `next_step_detail` alongside the start skeleton
   - Recommend exploration mode explicitly

4. `tool_catalog.py` -- update `rd_run_start` example to show `exploration_mode` and
   `branch_hypotheses` parameters.

**Hypothesis generation approach:** The hypotheses are guidance text, not ML model
selection. The entry generates domain-agnostic placeholders and presents them for
user confirmation. Example:
```python
def _generate_branch_hypotheses(intent: str) -> list[str]:
    return [
        f"Approach A: primary method for {intent[:50]}",
        f"Approach B: alternative method for {intent[:50]}",
        f"Approach C: baseline comparison for {intent[:50]}",
    ]
```
The user can then modify/confirm before passing to `rd_agent`.

### Anti-Patterns to Avoid

- **Partial rename:** Renaming `disposition` in models but missing a test assertion
  or a dict key access. Use grep exhaustively.
- **Breaking existing tests first:** The test `test_executable_paused_route_uses_detail_hint_without_auto_skeleton`
  asserts `detail_hint` is truthy and `next_step_detail` is empty. This test must be
  updated (not just made to pass) since the contract changes.
- **Materializing next-stage on replay/block:** Only materialize on COMPLETED
  transitions. Replay and block should NOT seed the next stage.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Skeleton generation | Custom string templates per stage | `_minimum_continuation_skeleton` already in operator_guidance.py | DRY, tested, consistent format |
| Stage sequencing | Hardcoded if/else chains | `STAGE_TO_NEXT_SKILL` map and `StageKey` enum ordering | Already canonical, used by tool_catalog |
| Branch hypothesis text | LLM-generated creative text | Simple template strings in the guidance builder | Phase 25 is about UX surface, not AI hypothesis quality |

## Common Pitfalls

### Pitfall 1: Pydantic extra="forbid" breaking on renamed fields
**What goes wrong:** After renaming `disposition` to `recovery_assessment` in the model,
any code that constructs the model with `disposition=` kwarg will raise a
`ValidationError` ("Extra inputs are not permitted").
**Why it happens:** `extra="forbid"` rejects unknown field names.
**How to avoid:** Run full test suite after each model rename. Grep for ALL usages
before committing.
**Warning signs:** `ValidationError: 1 validation error for RecoveryAssessment`

### Pitfall 2: structuredContent dict key mismatch with test assertions
**What goes wrong:** Tests assert `result["structuredContent"]["decision"]["disposition"]`
but the key is now `recovery_assessment`.
**Why it happens:** Dict key access is stringly typed -- no IDE/type-checker catches it.
**How to avoid:** Grep for `"disposition"` in all test files after rename.
**Warning signs:** `KeyError: 'disposition'` in test output.

### Pitfall 3: Stage materialization creating duplicate snapshots
**What goes wrong:** If `publish_stage_complete` is called when a NOT_STARTED snapshot
for the next stage already exists, it could create a duplicate.
**Why it happens:** `_publish_stage_snapshot` replaces snapshots by (stage_key, stage_iteration)
but a pre-existing NOT_STARTED might have iteration=1 which is the same as the new one.
**How to avoid:** The existing `_publish_stage_snapshot` dedup logic handles this:
it filters out matching (stage_key, stage_iteration) before appending.
**Warning signs:** Multiple NOT_STARTED snapshots in branch.stages for the same stage_key.

### Pitfall 4: test_executable_paused_route asserts old behavior
**What goes wrong:** `test_executable_paused_route_uses_detail_hint_without_auto_skeleton`
(line 100-108 in test_phase24_operator_guidance.py) asserts `detail_hint` is truthy and
`next_step_detail` is empty. Phase 25 inverts this.
**Why it happens:** The test was written for Phase 24's selective-detail pattern.
**How to avoid:** Update the test to assert `next_step_detail` is present and
`detail_hint` is None/absent.
**Warning signs:** Test failure with clear assertion message.

### Pitfall 5: ExecutionMode vs ExplorationMode confusion
**What goes wrong:** The CONTEXT says "change execution_mode default to exploration"
but `ExecutionMode` is `GATED | UNATTENDED`. `ExplorationMode` is `EXPLORATION | CONVERGENCE`.
These are different enums with different purposes.
**Why it happens:** The terminology overlaps.
**How to avoid:** `execution_mode` stays as `ExecutionMode` (controls gated vs unattended).
Add `exploration_mode` as a separate field defaulting to `ExplorationMode.EXPLORATION`.
**Warning signs:** Type errors mixing the two enums.

## Code Examples

### Example 1: Adding outcome field to rd_propose completed path
```python
# Current (rd_propose.py, line 234-248, completed path):
return _tool_response(
    {
        "owned_stage": OWNED_STAGE_KEY.value,
        "operator_guidance": guidance["payload"],
        "decision": decision.model_dump(mode="json"),
        # ... other fields
    },
    guidance["text"],
)

# Fixed:
return _tool_response(
    {
        "owned_stage": OWNED_STAGE_KEY.value,
        "outcome": "completed",  # ADD THIS
        "operator_guidance": guidance["payload"],
        "decision": decision.model_dump(mode="json"),
        # ... other fields
    },
    guidance["text"],
)
```

### Example 2: Always providing next_step_detail in stage guidance
```python
# Current pattern in entry files (e.g., rd_propose.py completed path):
guidance = build_stage_guidance_response(
    run_id=run_id,
    branch_id=branch_id,
    stage_key=OWNED_STAGE_KEY.value,
    state_descriptor="completed successfully",
    routing_reason="Reason: framing completed and prepared the build handoff.",
    exact_next_action=f"Next action: continue {run_id} / {branch_id} with rd-code.",
    recommended_next_skill="rd-code",
    # next_step_detail NOT passed
)

# Fixed:
guidance = build_stage_guidance_response(
    run_id=run_id,
    branch_id=branch_id,
    stage_key=OWNED_STAGE_KEY.value,
    state_descriptor="completed successfully",
    routing_reason="Reason: framing completed and prepared the build handoff.",
    exact_next_action=f"Next action: continue {run_id} / {branch_id} with rd-code.",
    recommended_next_skill="rd-code",
    next_step_detail=_minimum_continuation_skeleton(run_id=run_id, branch_id=branch_id),
)
```

Note: `_minimum_continuation_skeleton` is already defined in
`v3/orchestration/operator_guidance.py`. Entry files need to import it.

### Example 3: RecoveryAssessment field rename
```python
# Before (v3/contracts/recovery.py):
class RecoveryAssessment(BaseModel):
    disposition: RecoveryDisposition

# After:
class RecoveryAssessment(BaseModel):
    recovery_assessment: RecoveryDisposition
```

### Example 4: Multi-branch start guidance with hypotheses
```python
# New build_start_new_run_guidance in operator_guidance.py:
def build_start_new_run_guidance(*, user_intent: str) -> OperatorGuidance:
    intent_text = user_intent.strip()
    hypotheses = _generate_branch_hypotheses(intent_text)
    hypothesis_lines = "\n".join(f"  - {h}" for h in hypotheses)
    skeleton = _minimum_start_skeleton(intent_text)
    branch_skeleton = (
        f'{skeleton} '
        f'exploration_mode="exploration" '
        f'branch_hypotheses={hypotheses!r}'
    )
    return OperatorGuidance(
        recommended_next_skill="rd-agent",
        current_state=(
            "Current state: no paused run is active, so a new run can start (`start_new_run`). "
            "Multi-branch exploration is recommended."
        ),
        routing_reason=(
            "Reason: plain-language intent suggests a research task. "
            "I suggest exploring these directions:\n" + hypothesis_lines
        ),
        exact_next_action=(
            "Next action: start a new run with rd-agent in exploration mode. "
            "Confirm or modify the suggested branch hypotheses, then start."
        ),
        next_step_detail=branch_skeleton,
    )
```

## State of the Art

| Old Approach (Phase 24) | Current Approach (Phase 25) | Impact |
|--------------------------|----------------------------|--------|
| `detail_hint` for executable paths, `next_step_detail` for blocked only | `next_step_detail` always present, `detail_hint` removed | Every consumer gets actionable skeleton |
| `execution_mode` defaults to `gated` | `exploration_mode` defaults to `exploration` | Multi-branch is the natural UX |
| No outcome field on rd_propose, rd_code, rd_evaluate | Consistent `outcome` field on all 4 entries | Programmatic consumers can branch on outcome |
| `decision.disposition` | `decision.recovery_assessment` | Self-documenting pre-execution semantics |
| Stage completion leaves current_stage_key on completed stage | Materializes NOT_STARTED next-stage snapshot | Programmatic consumers read branch.current_stage_key for position |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (via `uv run python -m pytest`) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run python -m pytest tests/test_phase24_operator_guidance.py tests/test_phase24_stage_next_step_guidance.py -x -q` |
| Full suite command | `uv run python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SC-1 | route_user_intent start_new_run includes hypotheses | unit | `uv run python -m pytest tests/test_phase25_multi_branch_ux.py::test_start_new_run_guidance_includes_hypotheses -x` | Wave 0 |
| SC-2 | rd_run_start schema exposes exploration_mode and branch_hypotheses | unit | `uv run python -m pytest tests/test_phase25_multi_branch_ux.py::test_run_start_request_accepts_exploration_fields -x` | Wave 0 |
| SC-3 | All paths include next_step_detail skeleton | unit | `uv run python -m pytest tests/test_phase25_guidance_completeness.py -x` | Wave 0 |
| SC-4 | Stage completion materializes NOT_STARTED next-stage | unit | `uv run python -m pytest tests/test_phase25_stage_materialization.py -x` | Wave 0 |
| SC-5 | All 4 entries expose consistent outcome field | unit | `uv run python -m pytest tests/test_phase25_outcome_consistency.py -x` | Wave 0 |
| SC-6 | disposition renamed to recovery_assessment | unit | `uv run python -m pytest tests/test_phase25_disposition_rename.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_phase24_operator_guidance.py tests/test_phase24_stage_next_step_guidance.py tests/test_phase25_*.py -x -q`
- **Per wave merge:** `uv run python -m pytest tests/ -x -q`
- **Phase gate:** Full 163+ test suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_phase25_outcome_consistency.py` -- covers SC-5: assert all 4 entries return outcome for every disposition path
- [ ] `tests/test_phase25_guidance_completeness.py` -- covers SC-3: assert next_step_detail present and detail_hint absent on all paths
- [ ] `tests/test_phase25_disposition_rename.py` -- covers SC-6: assert field name is recovery_assessment in models and structuredContent
- [ ] `tests/test_phase25_stage_materialization.py` -- covers SC-4: assert NOT_STARTED snapshot created after completion
- [ ] `tests/test_phase25_multi_branch_ux.py` -- covers SC-1, SC-2: exploration_mode default, hypotheses in guidance

## Open Questions

1. **Backward compatibility of persisted state**
   - What we know: The `disposition` field rename will break deserialization of any
     existing `.state/` directories with persisted `RecoveryAssessment` JSON.
   - What's unclear: Whether any real user state exists that would break.
   - Recommendation: Accept the break. This is a dev-phase project with no production
     persistence. Document in commit message.

2. **Hypothesis generation quality**
   - What we know: Context says auto-generate 2-3 hypotheses like "ResNet18 transfer",
     "EfficientNet-B0", "Simple CNN baseline".
   - What's unclear: Whether the entry has enough context (just `user_intent` string)
     to generate domain-specific hypotheses.
   - Recommendation: Use generic placeholders ("Approach A: primary method", etc.)
     with clear operator-facing language that says "modify these before starting."
     Domain-specific generation is a later-phase concern.

3. **detail_hint field removal vs deprecation**
   - What we know: User discretion says either remove or keep as deprecated.
   - Recommendation: Remove the field entirely from `OperatorGuidance`. The `extra="forbid"`
     constraint means keeping it as `None` still wastes contract surface. Clean removal
     is safer since it will fail loudly if any caller still passes it.

## Sources

### Primary (HIGH confidence)
- Direct code inspection of all 17 source files listed in Architecture Patterns
- Direct code inspection of all 4 test files listed in CONTEXT.md canonical_refs
- `pyproject.toml` for test framework and dependency versions
- `v3/contracts/recovery.py` for Pydantic model constraints
- `v3/orchestration/stage_transition_service.py` for materialization gap

### Secondary (MEDIUM confidence)
- CONTEXT.md success criteria for requirement-to-test mapping
- Phase 22/23/24 CONTEXT.md for locked prior decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, fully inspected existing code
- Architecture: HIGH - every modification target identified with line numbers
- Pitfalls: HIGH - all derived from direct code inspection of Pydantic constraints and test assertions
- Multi-branch UX: MEDIUM - hypothesis generation approach is discretionary, needs user validation

**Research date:** 2026-03-23
**Valid until:** 2026-04-22 (30 days - stable project, internal-only)
