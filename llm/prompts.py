"""Prompt templates for structured LLM calls.

Each function builds a rich prompt string for a specific pipeline stage.
The LLMAdapter appends JSON schema enforcement separately — these templates
focus on role, context, and evaluation criteria.
"""

from __future__ import annotations

from typing import List, Optional


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
