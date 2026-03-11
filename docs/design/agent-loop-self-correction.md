# Agent Loop Self-Correction

## Overview

The CoSTEER (Collaborative Scientific Task-oriented Evolution and Engineering Reasoning) loop is the core of the R&D-Agent's coding workflow. While the original framework handles iterative improvement, it was previously fragile when facing categorical failures, often resulting in loop termination or silent degradations.

This self-correction mechanism enhances the loop by introducing structured exception handling, shared feedback enrichment, and improved visibility into the R&D process. It allows the agent to recognize when it has failed, categorize the failure, and adjust its strategy accordingly without necessarily stopping the entire experiment.

## Design Principles (UPDATED)

1.  **Observability First**: Ensure every failure, including those handled by fallback mechanisms, is explicitly visible in the trace and feedback records.
2.  **Structural Grace**: Use a dedicated exception hierarchy to distinguish between fatal system errors and recoverable iteration-level failures.
3.  **Knowledge Accumulation**: Capture and save findings from failed experiments to prevent the agent from repeating the same mistakes in future branches.
4.  **Feedback Fidelity**: Preserve the full multi-dimensional structure of FC-3 (Reasoning Pipeline) feedback throughout the CoSTEER iterations.
5.  **Minimal Core Intrusion**: Maintain the integrity of the core loop engine by using thin adapters and scenario-level routing for self-correction logic.

## What Was Implemented

### Exception Hierarchy

A new exception hierarchy was introduced in `core/correction/exceptions.py` to manage iteration-level failures:
- `SkipIterationError`: The base exception for failures that should be archived but not terminate the loop.
- `CoderError`: Raised when code generation or validation fails.
- `RunnerError`: Raised when the execution of the artifact fails.

The `LoopEngine` in `core/loop/engine.py` now specifically catches `SkipIterationError`, archives the failed state, and continues to the next iteration instead of crashing.

### Failure Knowledge Saving

The `CoSTEER` implementation in `core/loop/costeer.py` was updated to save experiment knowledge unconditionally. 
- Previously, knowledge was only saved on successful iterations.
- Now, even if an iteration fails, the findings are stored with a `"success": "False"` metadata tag.
- This allows the `MemoryService` to retrieve "what NOT to do" in subsequent R&D steps.

### Shared Feedback Enricher

The logic for injecting feedback into new code generation requests was consolidated into `core/correction/feedback_enricher.py`.
- Replaces duplicate and incomplete `_enrich_*_with_feedback()` methods across different scenario coders.
- Properly reads all four dimensions of FC-3 feedback: `_costeer_feedback_execution`, `_costeer_feedback_code`, `_costeer_feedback_return`, and the overall reasoning (`_costeer_feedback`).
- Ensures the LLM receives the most specific signals available from previous failures.

### Degradation Visibility (Quant)

In the `quant` scenario, silent false positives were addressed by updating the `QuantFeedbackAnalyzer`.
- It now inspects the `_code_source` field in the hypothesis.
- If `_code_source == "failed"`, indicating that fallback/template code was used due to an LLM failure, the result is marked as `acceptable = False` and the reason is prefixed with `[DEGRADED]`.

## Constraint Changes

The original design stated "不修改 core/loop/costeer.py 和 core/loop/step_executor.py 的主流程" (Do not modify the main flows of core/loop/costeer.py and core/loop/step_executor.py).

This constraint was relaxed because:
- **Failure knowledge saving** required modifying the save condition in `costeer.py` to ensure failed experiments are recorded.
- **Skip routing** required updating the exception handling logic in `engine.py` to recognize `SkipIterationError`.
- These changes were minimal (2-3 lines each) and were necessary to achieve the core goals of the self-correction mechanism without creating complex workarounds.

## Future Work (Not Yet Implemented)

- **Layer 3: Scenario-Level Self-Healing**: Implementing advanced healing strategies such as dynamic timeout relaxation, automatic re-analysis of failed traces, and selective trace resets.
- **WithdrawLoopError / Checkpoint Recovery**: Allowing the agent to explicitly rollback to the last known good state when it detects it's on a dead-end path.
- **CorrectionTracker / Early Stop**: A stateful tracker to detect repeated failure patterns or stagnating metrics, enabling the agent to stop wasting tokens on hopeless iterations.
- **FailureClassifier**: Automated categorization of failures into transient (network), structural (syntax/import), or semantic (logic) categories to guide specific retry hints.
- **MCTS Failure Propagation**: Feeding failure signals back into the exploration manager to adjust branch selection weights, effectively "pruning" paths that frequently lead to self-correction events.
