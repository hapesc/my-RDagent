# Phase 25: Fix QA-discovered operator guidance and multi-branch UX gaps - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the 6 issues discovered during Codex-driven QA testing on a real
aerial-cactus-identification project, and expose multi-branch exploration as a
first-class default UX rather than a hidden power-user feature. This phase
covers: multi-branch UX surface and default mode, guidance completeness across
all paths, stage state materialization, disposition semantic alignment, and
committing the uncommitted Phase 24 rename/validation fixes. The full 4-layer
R&D-Agent convergence mechanism (Adaptive DAG, cross-branch communication,
Multi-trace Merge, Holdout validation) is deferred to Phases 26-28.

</domain>

<decisions>
## Implementation Decisions

### Multi-branch UX exposure and default mode
- `execution_mode` default changes from `gated` to `exploration` for new runs.
- `exploration_mode` and `branch_hypotheses` must be exposed in the
  `rd_run_start` input schema and tool catalog description.
- `route_user_intent` must recommend multi-branch exploration in its
  `start_new_run` guidance, including auto-generated branch hypotheses in
  `next_step_detail`.
- When routing detects a research-type intent, the system should auto-generate
  2-3 branch hypotheses (e.g., "ResNet18 transfer", "EfficientNet-B0",
  "Simple CNN baseline") and present them in the guidance for user confirmation
  or modification.
- Users can still explicitly request `gated` mode for single-branch work.

### Guidance completeness — all paths give copy-pasteable skeletons
- Abandon the Phase 24 `selective-detail` / `detail_hint` pattern.
- Every operator guidance response — completed, blocked, reused, replay,
  review, new-run — must include a `next_step_detail` field with a
  copy-pasteable parameter skeleton for the recommended next skill.
- Example for framing completed:
  `rd-code run_id="run-001" branch_id="branch-001" summary="..." artifact_ids=[...]`
- The `detail_hint` field ("If you want, I can expand...") is removed; the
  skeleton is always present.

### Stage state materialization on completion
- When a stage entry completes successfully, it must automatically create a
  NOT_STARTED snapshot for the next stage and update
  `branch.current_stage_key` to the next stage key.
- This ensures programmatic consumers of `structuredContent` can read
  `branch_after.current_stage_key` to know the current position without
  parsing guidance text.
- The materialized next-stage snapshot should include a `summary` like
  "Prepared and requires preflight before execution."

### Disposition semantic alignment (outcome + rename)
- Add a consistent `outcome` field to `structuredContent` for all 4 stage
  entries (rd_propose, rd_code, rd_execute, rd_evaluate). rd_execute already
  has this; the other 3 must match.
- Valid outcome values: `completed`, `blocked`, `preflight_blocked`, `reused`,
  `replay`, `review`.
- Rename `decision.disposition` to `decision.recovery_assessment` across all
  stage entries and the `ResumeDecision` model to make its pre-execution
  semantics self-documenting.
- `operator_guidance` continues to reflect post-execution results;
  `decision.recovery_assessment` continues to reflect the entry-time recovery
  state. They serve different consumers and do not need to agree.

### Uncommitted Phase 24 fixes
- The working tree contains uncommitted renames (`project_operator_guidance` →
  `operator_guidance_to_dict`, extracted `build_stage_guidance_response`) and
  validation additions (`_REQUIRED_TEXT_FIELDS`). These must be committed as
  the first step before any Phase 25 work begins.

### Claude's Discretion
- Exact wording of auto-generated branch hypotheses.
- Whether `detail_hint` field is removed from `OperatorGuidance` contract or
  kept as deprecated/unused.
- Implementation order of the 6 fixes within Phase 25.

</decisions>

<specifics>
## Specific Ideas

- Multi-branch should feel like the natural way to use rdagent — the system
  should say "I suggest exploring these 3 directions" not "you can optionally
  pass branch_hypotheses."
- The R&D-Agent convergence mechanism has 4 layers (documented below) that
  Phase 25 does NOT implement but that Phases 26-28 will build on:
  1. Adaptive DAG path management with SelectParents + pruning
  2. Cross-branch collaborative communication (global best injection +
     probabilistic sampling exchange)
  3. Multi-trace solution merge (identify complementary components + synthesize
     unified solution)
  4. Aggregated validation with holdout set + standardized ranking
- Phase 25's multi-branch UX should be designed so it naturally extends into
  these 4 layers without breaking changes.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase boundary and requirements
- `.planning/ROADMAP.md` — Phase 25 entry and v1.3 milestone context
- `.planning/REQUIREMENTS.md` — All v1 requirements (complete); Phase 25 is a
  fix/enhancement phase with no new formal requirements
- `.planning/STATE.md` — Current continuity truth

### Prior phase decisions that still apply
- `.planning/phases/22-intent-routing-and-continuation-control/22-CONTEXT.md`
  — Locked routing fields (`current_state`, `routing_reason`,
  `exact_next_action`, `recommended_next_skill`)
- `.planning/phases/23-preflight-and-state-truth-hardening/23-CONTEXT.md` —
  Locked preflight truth, blocked-vs-executable semantics
- `.planning/phases/24-operator-guidance-and-next-step-ux/24-CONTEXT.md` —
  Locked three-part guidance shape, repair-first ordering, shared
  OperatorGuidance contract

### QA evidence
- QA was run via Codex MCP on `/Users/michael-liang/Code/aerial-cactus-identification`
  with route_user_intent, rd_propose, rd_code, rd_execute, rd_evaluate
- Codex end-to-end pipeline QA output at `/tmp/rdagent-v3-pipeline-qa.*/`
- Code review findings from the current conversation (CRITICAL: hardcoded
  run-001, HIGH: _stage_guidance duplication, MEDIUM: naming/validation)

### Key source files to modify
- `v3/contracts/operator_guidance.py` — OperatorGuidance model (remove
  detail_hint, ensure next_step_detail always populated)
- `v3/orchestration/operator_guidance.py` — Builders, renderer, STAGE_TO_NEXT_SKILL
- `v3/entry/rd_agent.py` — route_user_intent (multi-branch guidance,
  hypotheses generation, exploration default)
- `v3/entry/rd_propose.py` — outcome field, recovery_assessment rename,
  next-stage materialization
- `v3/entry/rd_code.py` — same as rd_propose
- `v3/entry/rd_execute.py` — outcome already exists; recovery_assessment rename,
  next-stage materialization
- `v3/entry/rd_evaluate.py` — same as rd_propose
- `v3/entry/tool_catalog.py` — expose exploration_mode/branch_hypotheses in
  rd_run_start spec
- `v3/orchestration/resume_planner.py` — ResumeDecision.disposition rename
- `v3/contracts/recovery.py` — RecoveryDisposition (potentially rename)

### Verification anchors
- `tests/test_phase24_operator_guidance.py` — Existing route guidance tests
- `tests/test_phase24_stage_next_step_guidance.py` — Existing stage guidance
  matrix tests
- `tests/test_phase19_tool_guidance.py` — Tool catalog vocabulary alignment
- `tests/test_v3_tool_cli.py` — Tool describe surface tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `v3/orchestration/operator_guidance.py` already has `build_stage_guidance_response`
  (extracted from the 4 entry files in uncommitted fixes) — this is the shared
  guidance builder that all entries should use.
- `v3/orchestration/multi_branch_service.py` has `run_exploration_round` and
  `run_convergence_round` — the skeleton for multi-branch is already there.
- `v3/contracts/exploration.py` has `ExplorationMode` enum with EXPLORATION
  and CONVERGENCE values.
- `v3/orchestration/selection_service.py` has `select_next_branch` — branch
  recommendation logic exists.

### Established Patterns
- Stage entries follow a consistent pattern: preflight check → recovery
  decision → branch by disposition → publish stage outcome → return guidance.
- `structuredContent` includes `owned_stage`, `decision`, `run`, `branch_before`,
  `branch_after`, `stage_after` — the `outcome` field should sit at the same
  top level.
- Tool catalog specs use `_follow_up()` helper with `_STAGE_SKILL_LIST` from
  shared `STAGE_TO_NEXT_SKILL` — multi-branch vocabulary should integrate here.

### Integration Points
- `rd_agent.py:268` — `branch_hypotheses` parameter already wired to
  MultiBranchService; the gap is in routing and schema exposure.
- `rd_agent.py:239` — `execution_mode` parameter exists but defaults to
  `ExecutionMode.GATED`; change default to `EXPLORATION`.
- `StageTransitionService` — may need extension to support auto-materializing
  the next stage snapshot on completion.

</code_context>

<deferred>
## Deferred Ideas

### Phase 26: Adaptive DAG Path Management
- SelectParents based on validation scores, generalization, overfitting risk
- Greedy exploitation within branches + dynamic pruning of underperforming paths
- First-layer diversity maximization

### Phase 27: Cross-branch Communication + Multi-trace Merge
- Global best injection into branch context
- Probabilistic sampling kernel for cross-branch experience sharing
- Identify complementary components across branches
- Synthesize unified solution from multiple branch successes

### Phase 28: Aggregated Validation and Holdout Calibration
- Collect top candidates from all exploration branches
- Create synthetic holdout set (90-10 split) for isolated re-evaluation
- Standardized ranking and single-best submission selection
- Overfitting prevention through multi-checkpoint validation

</deferred>

---

*Phase: 25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps*
*Context gathered: 2026-03-23*
