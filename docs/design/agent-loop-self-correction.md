# Agent Loop Self-Correction

## Overview

The CoSTEER (Collaborative Scientific Task-oriented Evolution and Engineering Reasoning) loop is the core of the R&D-Agent's coding workflow. While the original framework handles iterative improvement, it was previously fragile when facing categorical failures, often resulting in loop termination or silent degradations.

This self-correction mechanism enhances the loop by introducing structured exception handling, shared feedback enrichment, and improved visibility into the R&D process. It allows the agent to recognize when it has failed, categorize the failure, and adjust its strategy accordingly without necessarily stopping the entire experiment.

## Design Principles (UPDATED)

Five principles from the original RD-Agent drive the changes:

1.  **Exception-Driven Control Flow**: Use typed exceptions (`SkipIterationError`, `CoderError`, `RunnerError`) to distinguish between recoverable and fatal failures, enabling structured routing at each layer.
2.  **Failed Experiments Enter the Knowledge Base**: Save findings from failed experiments unconditionally, tagged with `success=False` metadata, so the agent learns from mistakes and avoids repeating them.
3.  **Recovery Granularity Matches Failure Scope**: A coding failure skips one iteration (not the entire run); a runner failure skips the execution step (not the coding step). Each error type is handled at the most appropriate level.
4.  **Healing Happens After Bookkeeping**: Always archive the failure state and save knowledge BEFORE attempting recovery. This ensures no information is lost even if recovery itself fails.
5.  **Each Layer Uses Its Most Natural Information Carrier**: The core loop uses exceptions for control flow, scenario plugins use `FeedbackRecord` fields for enrichment, and the memory service uses metadata tags for retrieval filtering.

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
