# Implementation Plan: P0 Codegen Reliability & CoSTEER Integration

## 1. Objective

To implement the codegen reliability specification by rewriting scenario coders to use LLM-generated code correctly, integrating pre-execution validation, and ensuring full compatibility with the CoSTEER multi-round iteration loop.

## 2. Wave Structure

### Wave 1: Foundation & Specs
- [x] Create formal specification docs.
- [ ] Create formal implementation plan (this document).
- [ ] Define TDD skeletons and shared test fixtures for codegen scenarios.
- [ ] Update `CodeDraft` schemas to support explicit `code` and `metadata` fields.

### Wave 2: Shared Components & Observability
- [ ] Implement `ASTValidator` for syntax and safety checks.
- [ ] Implement `PlaceholderDetector` for pre-execution rejection of partial code.
- [ ] Enhance `LLMAdapter` to record `code_source` and duration metadata in trace events.
- [ ] Redesign `coding_prompt()` in `llm/prompts.py` to support structured multi-file output.

### Wave 3: Scenario Coder Rewrites
- [ ] **DataScienceCoder**: Remove template-only fallback. Implement `develop()` using structured LLM output with template fallback ONLY for mock providers.
- [ ] **QuantCoder**: Add `compute_factor` signature validation and error-feedback integration for backtest failures.
- [ ] **SyntheticResearchCoder**: Enrich `artifact.description` with full research content for CoSTEER rounds.

### Wave 4: Integration & Sampling
- [ ] Ensure all Coders correctly implement `_enrich_proposal_with_feedback`.
- [ ] Validate `CoSTEEREvolver` compatibility with the new Coder return values.
- [ ] Verify debug-mode sampling (`RD_AGENT_DEBUG_MODE`) does not interfere with reliability checks.

### Wave 5: Verification & Smoke Tests
- [ ] Run real provider smoke tests for all three scenarios (Data Science, Quant, Synthetic Research).
- [ ] Execute full regression suite with a focus on `CoSTEER` convergence.
- [ ] Validate trace event correctness for observability metrics.

### Wave FINAL: Review & Delivery
- [ ] Trigger 4 parallel review agents for independent verification of:
    - Spec compliance.
    - Security/AST safety.
    - Backward compatibility.
    - Code quality.

## 3. Success Criteria

- Template fallback occurs < 5% of the time with real LLM providers.
- `CoSTEER` successfully iterates on code failures in at least 80% of multi-round test cases.
- `ASTValidator` rejects invalid syntax before it reaches the execution sandbox.
- All 6 waves are completed and verified.
