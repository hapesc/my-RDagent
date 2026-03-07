"""Prompt templates for structured LLM calls.

Each function builds a rich prompt string for a specific pipeline stage.
The LLMAdapter appends JSON schema enforcement separately — these templates
focus on role, context, and evaluation criteria.
"""

from __future__ import annotations

import dataclasses
import json
from typing import List, Optional

from llm.schemas import ExperimentDesign


def _build_schema_hint(schema_cls: type) -> str:
    if not dataclasses.is_dataclass(schema_cls):
        return ""
    example = {}
    for field_obj in dataclasses.fields(schema_cls):
        ann = str(field_obj.type)
        if ann in ("str", "<class 'str'>"):
            example[field_obj.name] = "string"
        elif ann in ("float", "<class 'float'>"):
            example[field_obj.name] = 0.0
        elif ann in ("bool", "<class 'bool'>"):
            example[field_obj.name] = True
        elif "List[str]" in ann:
            example[field_obj.name] = ["string"]
        elif "List[int]" in ann:
            example[field_obj.name] = [0]
        elif "List[float]" in ann:
            example[field_obj.name] = [0.0]
        else:
            example[field_obj.name] = "value"
    return json.dumps(example, indent=2)


def _iteration_strategy(iteration: int) -> str:
    if iteration == 0:
        return (
            "This is the FIRST iteration. Prioritize a well-scoped, executable baseline "
            "over novelty. Pick the simplest credible approach that produces measurable results."
        )
    if iteration <= 2:
        return (
            f"Iteration {iteration}: You have prior results to build on. "
            "Identify the single weakest aspect of previous work and propose a targeted improvement. "
            "Do NOT restart from scratch."
        )
    return (
        f"Iteration {iteration}: The exploration is maturing. "
        "Focus on refinement, ablation, or addressing a specific failure mode. "
        "Diminishing returns are expected — be honest about whether to continue."
    )


def proposal_prompt(
    task_summary: str,
    scenario_name: str,
    iteration: int,
    previous_proposals: Optional[List[str]] = None,
) -> str:
    history_block = ""
    if previous_proposals:
        items = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(previous_proposals[-3:]))
        history_block = (
            f"\n## Previous Proposals\n{items}\n"
            f"You MUST differentiate from these. Either refine a promising direction "
            f"or pivot to an unexplored angle with clear justification.\n"
        )

    strategy = _iteration_strategy(iteration)

    return (
        f"You are a research scientist planning the next experiment in an iterative R&D loop.\n"
        f"\n"
        f"## Task\n"
        f"{task_summary}\n"
        f"\n"
        f"## Context\n"
        f"- Scenario: {scenario_name}\n"
        f"- Iteration: {iteration}\n"
        f"- Strategy: {strategy}\n"
        f"{history_block}"
        f"\n"
        f"## Output Fields\n"
        f"- `summary`: 1-3 sentence research proposal. State the independent variable, "
        f"dependent variable, and evaluation method explicitly.\n"
        f"- `constraints`: 2-4 technical risks that could invalidate the experiment. "
        f"Each must name a specific failure mode (e.g. 'gradient explosion with LR > 1e-3'), "
        f"not a vague concern.\n"
        f"- `virtual_score`: Feasibility estimate 0.0-1.0. "
        f"0.0=impossible, 0.3=risky, 0.6=likely, 0.9=near-certain. Justify briefly in the summary.\n"
    )


def coding_prompt(
    proposal_summary: str,
    constraints: List[str],
    experiment_node_id: str,
    workspace_ref: str,
    scenario_name: str,
) -> str:
    constraints_block = "\n".join(f"  - {c}" for c in constraints) if constraints else "  (none)"

    return (
        f"You are a research engineer translating a proposal into an executable experiment design.\n"
        f"\n"
        f"## Research Proposal\n"
        f"{proposal_summary}\n"
        f"\n"
        f"## Known Risks\n"
        f"{constraints_block}\n"
        f"\n"
        f"## Experiment Context\n"
        f"- Scenario: {scenario_name}\n"
        f"- Node ID: {experiment_node_id}\n"
        f"- Workspace: {workspace_ref}\n"
        f"\n"
        f"## Output Fields\n"
        f"- `artifact_id`: snake_case identifier with version suffix (e.g. `lr_ablation_v2`).\n"
        f"- `description`: 2-3 sentences covering: (1) what runs, (2) what it measures, "
        f"(3) what output files are produced.\n"
        f"- `location`: Use the workspace path provided above.\n"
    )


def feedback_prompt(
    hypothesis_text: str,
    exit_code: int,
    score_text: str,
    logs_summary: str,
    iteration: int,
) -> str:
    exec_status = "succeeded" if exit_code == 0 else f"FAILED (exit_code={exit_code})"
    logs_block = logs_summary[:500] if logs_summary else "(no logs available)"

    return (
        f"You are a research reviewer evaluating experimental results.\n"
        f"\n"
        f"## Experiment (iteration {iteration})\n"
        f"- Hypothesis: {hypothesis_text or '(not specified)'}\n"
        f"- Execution: {exec_status}\n"
        f"- Score: {score_text}\n"
        f"\n"
        f"## Execution Logs\n"
        f"{logs_block}\n"
        f"\n"
        f"## Evaluation Guide\n"
        f"Analyze in this order:\n"
        f"1. Execution: Did the code run correctly? Any errors, warnings, or unexpected behavior in logs?\n"
        f"2. Scientific merit: Is the hypothesis testable? Was the methodology sound?\n"
        f"3. Results: Do the score and logs support or refute the hypothesis? "
        f"If the score looks like a placeholder (0.0, 'none'), ignore it and judge on execution quality.\n"
        f"4. Next steps: What specific change would yield the most information gain?\n"
        f"\n"
        f"## Output Fields\n"
        f"- `decision`: true if this research direction is worth continuing, false to abandon.\n"
        f"- `acceptable`: true if the experiment met minimum quality (ran correctly, tested something meaningful).\n"
        f"- `reason`: 1-2 sentence verdict referencing specific evidence from above.\n"
        f"- `observations`: Key findings, anomalies, or patterns from the results.\n"
        f"- `code_change_summary`: ONE concrete, actionable change for the next iteration "
        f"(not a wish list — pick the single highest-leverage fix).\n"
    )


def reasoning_analysis_prompt(
    task_summary: str,
    scenario_name: str,
    iteration: int,
    previous_results: List[str],
    current_scores: List[float],
) -> str:
    strategy = _iteration_strategy(iteration)
    
    previous_block = ""
    if previous_results:
        items = "\n".join(f"  {i+1}. {result}" for i, result in enumerate(previous_results[-3:]))
        scores_text = ", ".join(f"{s:.3f}" for s in current_scores[-3:]) if current_scores else "N/A"
        previous_block = (
            f"\n## Previous Results\n"
            f"{items}\n"
            f"Performance scores: {scores_text}\n"
        )
    
    return (
        f"You are a research scientist analyzing the current state of an iterative R&D exploration.\n"
        f"\n"
        f"## Task\n"
        f"{task_summary}\n"
        f"\n"
        f"## Context\n"
        f"- Scenario: {scenario_name}\n"
        f"- Iteration: {iteration}\n"
        f"- Strategy: {strategy}\n"
        f"{previous_block}"
        f"\n"
        f"## Instructions\n"
        f"Analyze the current solution and its performance trajectory:\n"
        f"1. What aspects of the current approach are working well?\n"
        f"2. What are the key weaknesses or failure modes?\n"
        f"3. How do the current scores compare to the trajectory? Is progress stalling?\n"
        f"4. Which component (data, model, training, hyperparameters) is most likely the limiting factor?\n"
        f"\n"
        f"## Output Fields\n"
        f"- `strengths`: 2-3 aspects of the current solution that are working.\n"
        f"- `weaknesses`: 2-3 specific failure modes or bottlenecks.\n"
        f"- `current_performance`: Performance trajectory — improving, stagnating, or declining? "
        f"By how much per iteration? Summarize the current quantitative standing.\n"
        f"- `key_observations`: Single most likely limiting factor and any notable patterns "
        f"(e.g., 'learning rate too high causes gradient explosion after epoch 5').\n"
    )


def reasoning_identify_prompt(
    analysis_text: str,
    task_summary: str,
    scenario_name: str,
) -> str:
    return (
        f"You are a research scientist identifying the critical problem in an iterative exploration.\n"
        f"\n"
        f"## Task\n"
        f"{task_summary}\n"
        f"\n"
        f"## Analysis\n"
        f"{analysis_text}\n"
        f"\n"
        f"## Scenario\n"
        f"{scenario_name}\n"
        f"\n"
        f"## Instructions\n"
        f"Based on the analysis above, identify the SINGLE most critical problem or bottleneck:\n"
        f"1. Be specific: name the exact failure mode (not just 'accuracy is low').\n"
        f"2. Be evidence-based: cite specific observations from the analysis.\n"
        f"3. Prioritize by impact: which issue, if fixed, would yield the largest improvement?\n"
        f"4. Distinguish root cause from symptom: is this the underlying issue or a downstream effect?\n"
        f"\n"
        f"## Output Fields\n"
        f"- `problem`: Precise, specific description of the bottleneck "
        f"(e.g., 'gradient vanishing in LSTM gate computations after 20 timesteps').\n"
        f"- `severity`: How critical is this problem — 'low', 'medium', 'high', or 'critical'. "
        f"Consider impact on overall performance.\n"
        f"- `evidence`: 1-2 observations from the analysis that support this diagnosis.\n"
        f"- `affected_component`: Which component is most affected "
        f"(e.g., 'data_loading', 'model_architecture', 'optimizer', 'training_loop').\n"
    )


def reasoning_hypothesize_prompt(
    analysis_text: str,
    problem_text: str,
    task_summary: str,
    scenario_name: str,
) -> str:
    return (
        f"You are a research scientist formulating a scientific hypothesis about why a problem exists.\n"
        f"\n"
        f"## Task\n"
        f"{task_summary}\n"
        f"\n"
        f"## Analysis Context\n"
        f"{analysis_text}\n"
        f"\n"
        f"## Problem Identified\n"
        f"{problem_text}\n"
        f"\n"
        f"## Scenario\n"
        f"{scenario_name}\n"
        f"\n"
        f"## Instructions\n"
        f"Formulate a testable hypothesis about WHY this problem exists and WHAT change would address it:\n"
        f"1. Root cause: What mechanism (not just observation) leads to this failure?\n"
        f"2. Mechanism: How does the proposed change fix the mechanism?\n"
        f"3. Testability: What observable outcome would confirm or refute this hypothesis?\n"
        f"4. Plausibility: Is this hypothesis consistent with the domain knowledge and evidence?\n"
        f"\n"
        f"## Output Fields\n"
        f"- `hypothesis`: 2-3 sentence hypothesis about the root cause and the proposed fix. "
        f"Use 'if...then' language (e.g., 'If the issue is due to learning rate decay being "
        f"too aggressive, then switching to a constant LR will stabilize training').\n"
        f"- `mechanism`: Scientific reasoning behind this hypothesis — what causal mechanism "
        f"connects the root cause to the observed failure? Reference theory, prior work, or domain logic.\n"
        f"- `expected_improvement`: Estimated magnitude of improvement if hypothesis is correct "
        f"(e.g., '+2-5% accuracy', '3x faster convergence').\n"
        f"- `testable_prediction`: What observable outcome (metric, log pattern, artifact) "
        f"would confirm or refute this hypothesis?\n"
    )


def reasoning_design_prompt(
    analysis_text: str,
    problem_text: str,
    hypothesis_text: str,
    task_summary: str,
    scenario_name: str,
    iteration: int,
) -> str:
    strategy = _iteration_strategy(iteration)
    
    return (
        f"You are a research engineer designing a concrete experiment to test a hypothesis.\n"
        f"\n"
        f"## Task\n"
        f"{task_summary}\n"
        f"\n"
        f"## Analysis\n"
        f"{analysis_text}\n"
        f"\n"
        f"## Problem\n"
        f"{problem_text}\n"
        f"\n"
        f"## Hypothesis\n"
        f"{hypothesis_text}\n"
        f"\n"
        f"## Experiment Context\n"
        f"- Scenario: {scenario_name}\n"
        f"- Iteration: {iteration}\n"
        f"- Strategy: {strategy}\n"
        f"\n"
        f"## Instructions\n"
        f"Design a concrete, implementable experiment to test this hypothesis:\n"
        f"1. Independent variable: What will you change? (e.g., 'switch optimizer to Adam')\n"
        f"2. Control: What remains constant to isolate the effect?\n"
        f"3. Dependent variable: What metric will you measure?\n"
        f"4. Implementation: What code changes, data modifications, or configuration tweaks are needed?\n"
        f"5. Success criteria: What result would constitute a successful test?\n"
        f"\n"
        f"## Output Fields\n"
        f"- `summary`: 2-3 sentences summarizing the experiment design. State the independent variable, "
        f"control conditions, and measurement plan explicitly.\n"
        f"- `constraints`: 2-4 technical risks or assumptions that could invalidate this experiment. "
        f"Each must name a specific failure mode (e.g., 'gradient explosion with LR > 1e-3'), "
        f"not a vague concern.\n"
        f"- `virtual_score`: Feasibility estimate 0.0-1.0. "
        f"0.0=impossible, 0.3=risky, 0.6=likely, 0.9=near-certain. "
        f"Consider implementation complexity and expected information gain.\n"
        f"- `implementation_steps`: Ordered list of concrete code/config changes needed. "
        f"Each step should be actionable (e.g., 'Replace SGD optimizer with Adam in train.py line 42'), "
        f"not pseudocode.\n"
    )


def virtual_eval_prompt(
    candidates: List,
    task_summary: str,
    scenario_name: str,
    evaluation_criteria: str,
) -> str:
    candidates_block = ""
    if candidates:
        items = "\n".join(
            f"  Candidate {i}: {c.get('summary', '(no summary)')}"
            for i, c in enumerate(candidates)
        )
        candidates_block = f"\n## Candidates\n{items}\n"
    else:
        candidates_block = "\n## Candidates\n  (no candidates provided)\n"
    
    return (
        f"You are a research scientist evaluating and ranking candidate proposals by expected performance.\n"
        f"\n"
        f"## Task\n"
        f"{task_summary}\n"
        f"\n"
        f"## Scenario\n"
        f"{scenario_name}\n"
        f"{candidates_block}"
        f"\n"
        f"## Evaluation Criteria\n"
        f"{evaluation_criteria}\n"
        f"\n"
        f"## Instructions\n"
        f"Rank these candidates by expected performance given the evaluation criteria:\n"
        f"1. For each candidate, estimate how well it will perform on the criteria (feasibility, novelty, clarity).\n"
        f"2. Rank them from most to least promising.\n"
        f"3. Justify your top-N ranking with specific reasoning.\n"
        f"4. Flag any candidates with major technical risks or impossible constraints.\n"
        f"\n"
        f"## Output Fields\n"
        f"- `rankings`: List of ALL candidate indices ordered by expected performance "
        f"(e.g., [2, 0, 4, 1, 3] means Candidate 2 is best). Must include every candidate index exactly once.\n"
        f"- `reasoning`: Brief justification for the ranking — explain why top candidates are preferred "
        f"and flag any major risks or blockers for lower-ranked ones (2-5 sentences).\n"
        f"- `selected_indices`: Indices of the top candidates to advance to the next stage "
        f"(e.g., [2, 0] for top 2). Select the K most promising candidates.\n"
    )


def merge_traces_prompt(
    trace_summaries: List[str],
    task_summary: str,
    scenario_name: str,
) -> str:
    traces_text = "\n\n".join(
        f"### Trace {i + 1}\n{summary}" for i, summary in enumerate(trace_summaries)
    )
    schema_hint = _build_schema_hint(ExperimentDesign)
    return (
        "You are an expert research synthesizer specializing in {scenario_name} experiments.\n\n"
        "## Context\n"
        "A multi-branch exploration produced {n} completed research traces for the task:\n"
        "**Task**: {task_summary}\n\n"
        "## Completed Traces\n"
        "{traces_text}\n\n"
        "## Instruction\n"
        "Synthesize the BEST elements from all traces into ONE unified experiment design.\n"
        "- Combine strengths from different traces\n"
        "- Avoid weaknesses identified in any trace\n"
        "- Produce a design that is MORE effective than any individual trace\n\n"
        "## Output Fields\n"
        "Return a JSON object with these fields:\n"
        "- `summary`: A concise description of the merged experiment design\n"
        "- `constraints`: List of constraints from combined traces\n"
        "- `virtual_score`: Estimated quality score (0.0-1.0)\n"
        "- `implementation_steps`: Ordered list of concrete implementation steps\n\n"
        "## Schema\n"
        "```json\n{schema_hint}\n```"
    ).format(
        scenario_name=scenario_name,
        n=len(trace_summaries),
        task_summary=task_summary,
        traces_text=traces_text,
        schema_hint=schema_hint,
    )
