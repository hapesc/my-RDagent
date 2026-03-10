# Specification: P0 Codegen Reliability & CoSTEER Integration

## 1. Problem Statement

The current implementation of Scenario Coders in the Agentic R&D Platform suffers from a "hollow generation" problem. While the `CoSTEEREvolver` provides a robust multi-round iteration skeleton, the underlying Coder implementations often bypass LLM-generated code in favor of hardcoded templates or lack necessary validation and feedback enrichment.

- **data_science**: `DataScienceCoder` generates metadata via LLM but unconditionally writes a fixed template `_build_pipeline_script`. LLM-generated code is never used for execution.
- **quant**: `QuantCoder` uses LLM code but lacks a validation loop and structured feedback mechanism, making it prone to simple syntax or logic errors that could be caught before full backtesting.
- **synthetic_research**: Not a code-execution scenario, but its `artifact.description` is too sparse for `CoSTEEREvolver` to provide meaningful feedback during multi-round refinement.

## 2. Fallback Policy

To ensure reliability while maintaining backward compatibility for non-LLM environments, the following policy is enforced:

| Condition | Action | Observable Signal |
|-----------|--------|-------------------|
| Real provider + valid code | Write code, execute | Trace: `code_source=llm` |
| Real provider + empty/no code | RETRY with feedback (if multi-round), then FAIL | Trace: `code_source=failed` |
| Real provider + compile fails | RETRY with error feedback, then FAIL | Trace: `code_source=failed` |
| Real provider + AST safety fail | FAIL — do not execute | Trace: `code_source=rejected_safety` |
| Real provider + placeholder tokens | FAIL — pre-execution rejection | Trace: `code_source=rejected_placeholder` |
| No real provider (mock/None) | Use template as before (backward compat) | Trace: `code_source=template` |
| `COSTEER_MAX_ROUNDS=1` | Single attempt, no retry loop | Same as above per single attempt |

## 3. CoSTEER Integration Contract

When `RD_AGENT_COSTEER_MAX_ROUNDS > 1`, `StepExecutor` routes to `CoSTEEREvolver.evolve()`. The integration contract requires:

1. **Explicit Code Return**: `Coder.develop()` must return a `CodeArtifact` where the `description` field (or a dedicated code field in the future) contains the actual source code or rich content generated. This is critical because `CoSTEEREvolver._analyze_feedback()` uses `artifact.description` as the "code" parameter for the structured feedback prompt.
2. **Feedback Consumption**: Coders must implement `_enrich_proposal_with_feedback` to inject `_costeer_feedback` from the `ExperimentNode` into the next round's prompt.
3. **Structured Response**: LLM prompts must use `generate_structured` with schemas that explicitly separate code from metadata to avoid parsing ambiguity.

## 4. Per-Scenario Requirements

### 4.1 Data Science (Code Execution)
- Rewrite `DataScienceCoder` to prioritize LLM-generated code.
- Use a dedicated `CodeDraft` schema that includes a `code` field.
- Only fallback to `_build_pipeline_script` if no LLM provider is configured.

### 4.2 Quant (Code + Validation)
- Enhance `QuantCoder` with a pre-execution AST validation step.
- Ensure the `compute_factor` function signature is strictly enforced.
- Integrate structured feedback from backtest failures back into the coding prompt.

### 4.3 Synthetic Research (Text Only)
- Enrich `artifact.description` with a comprehensive summary of the research findings.
- Ensure `CoSTEER` rounds focus on content depth and topic coverage rather than code correctness.
- The "execution" step for this scenario is a "read-and-verify" operation on the generated text.

## 5. Observability

All codegen attempts must emit trace events with the following metadata:
- `code_source`: (llm | template | failed | rejected_safety | rejected_placeholder)
- `round_index`: The current CoSTEER iteration count.
- `validation_errors`: Any AST or linting errors found during pre-execution.
- `llm_duration_ms`: Time taken for LLM generation.

This data will be used to monitor the "Template Fallback Rate" and "CoSTEER Convergence Rate" in the Trace UI.
