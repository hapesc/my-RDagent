
## Task 2: FC-3 Reasoning Prompt Templates

### Key Patterns Established

**Prompt Structure Convention** (observed from proposal_prompt, codified for all 5 functions):
```
You are a [ROLE].

## [SECTION]
[content]

## Output Fields
- `field_name`: description
```

This structure:
1. Establishes LLM role upfront (critical for quality outputs)
2. Uses markdown-style section headers for clear navigation
3. Explicit output fields with backticks and descriptions
4. Consistent formatting across all prompts

### Function-Specific Patterns

**Analysis Stage** (reasoning_analysis_prompt):
- Role: research scientist analyzing state
- Uses _iteration_strategy() for iteration-aware guidance
- Takes previous_results (list) and current_scores (list)
- Outputs: strengths, weaknesses, trajectory, bottleneck_hypothesis

**Identify Stage** (reasoning_identify_prompt):
- Role: research scientist identifying problems
- Takes analysis_text as input for evidence-based reasoning
- Outputs: problem_statement (specific), evidence (cited), impact_estimate (quantified)
- Note: Single critical problem identification (not multiple)

**Hypothesize Stage** (reasoning_hypothesize_prompt):
- Role: research scientist formulating hypothesis
- Takes analysis + problem text for context
- Outputs: hypothesis (if-then), rationale (theory-based), testable_prediction (observable)
- Note: Explicitly asks for mechanistic explanation, not just correlation

**Design Stage** (reasoning_design_prompt):
- Role: research engineer (not scientist) — emphasis on implementation feasibility
- Uses _iteration_strategy() for iteration-aware design philosophy
- Outputs: 6 fields (description, independent_variable, control_conditions, measurement_plan, implementation_outline, success_criteria)
- Most detailed prompt — reflects that experimental design is the bottleneck

**Virtual Evaluation** (virtual_eval_prompt):
- Role: research scientist evaluating rankings
- Takes candidates list, evaluation_criteria as input
- Handles edge cases: empty list, single candidate, many candidates
- Outputs: ranking (indices), justifications (per candidate), risk_flags, confidence
- Note: Explicitly asks for index-based ranking for easy machine parsing

### Design Decisions Made

1. **Why separate Identify and Hypothesize stages?**
   - Identify focuses on problem *description* (what + evidence)
   - Hypothesize focuses on problem *explanation* (why + mechanism)
   - This separation prevents LLM from jumping to solutions prematurely

2. **Why Design gets _iteration_strategy()?**
   - Analysis also needs it (analyze how to iterate)
   - Design needs it (early iterations value speed over novelty)
   - Identify and Hypothesize don't need it (same rigor at all stages)

3. **Why virtual_eval uses dict list, not just strings?**
   - Allows future extension with other fields (not just summary)
   - Mirrors how proposals/designs will be formatted
   - Makes list formatting cleaner (.get('summary', '(no summary)'))

4. **Why 6 output fields for Design?**
   - Mirrors scientific method: experimental design requires:
     - Description (what you're doing)
     - Variable specification (what changes)
     - Controls (what stays same)
     - Measurement (how you measure)
     - Implementation (how to build it)
     - Success criteria (how to judge it)

### TDD Test Coverage Strategy

Created 26 tests across 5 test classes:

**Per-function coverage**:
- signature_and_return_type: verifies correct parameters and str return
- has_role_assignment: looks for "scientist" or "engineer" keyword
- has_output_fields_section: checks for "## Output Fields" marker
- (2-3 additional tests per function) for integration/context

**Edge cases covered**:
- virtual_eval_prompt with empty candidates list
- virtual_eval_prompt with single candidate (edge case for ranking)
- virtual_eval_prompt with 5 candidates (scaled test)
- Analysis with/without previous_results and scores
- Iteration strategy effects (iteration 0 vs iteration 2)

### Integration Lessons

1. **No LLM calling in prompts** — these are pure string builders
   - Enables testing without LLM providers
   - Enables composition (e.g., prompt A feeds into prompt B)
   - Keeps concerns separated (prompt engineering vs LLM interaction)

2. **Type hints matter**:
   - previous_results: List[str] not List (for clarity)
   - candidates: List (generic) because dicts with 'summary' field
   - Keeps signatures readable while allowing flexibility

3. **Context feeding pattern**:
   - analysis_text → identify_prompt
   - analysis_text + problem_text → hypothesize_prompt
   - analysis_text + problem_text + hypothesis_text → design_prompt
   - This feedforward structure is error-resistant (no circular deps)

### Commit Readiness

Files modified: llm/prompts.py (added 184 lines, 5 functions)
Files created: tests/test_prompts_fc3.py (356 lines, 26 tests)

All 210 tests pass (184 existing + 26 new).
No LSP errors. No regression in existing functions.
Ready for commit with Task 3.

---
**Session**: 2025-03-07 | **Status**: Complete ✓
