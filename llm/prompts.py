"""Prompt templates for structured LLM calls.

Each function builds a rich prompt string for a specific pipeline stage.
The LLMAdapter appends JSON schema enforcement separately — these templates
focus on role, context, and evaluation criteria.
"""

from __future__ import annotations

from typing import List, Optional


def proposal_prompt(
    task_summary: str,
    scenario_name: str,
    iteration: int,
    previous_proposals: Optional[List[str]] = None,
) -> str:
    history_block = ""
    if previous_proposals:
        items = "\n".join(f"  - {p}" for p in previous_proposals[-3:])
        history_block = f"\n## Previous Proposals (most recent {len(previous_proposals)})\n{items}\nAvoid repeating these. Build on prior findings or explore a different angle.\n"

    return (
        f"You are a research scientist planning the next experiment in an iterative R&D loop.\n"
        f"\n"
        f"## Task\n"
        f"{task_summary}\n"
        f"\n"
        f"## Context\n"
        f"- Scenario: {scenario_name}\n"
        f"- Iteration: {iteration}\n"
        f"{history_block}"
        f"\n"
        f"## Instructions\n"
        f"- `summary`: A clear, actionable 1-3 sentence research proposal. Be specific about methodology.\n"
        f"- `constraints`: List 2-5 concrete, technical challenges or risks (not generic platitudes).\n"
        f"- `virtual_score`: Estimated feasibility from 0.0 (impossible) to 1.0 (trivial). "
        f"Most genuine research is 0.3-0.8.\n"
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
        f"You are a research engineer. Given a research proposal, design a concrete experimental artifact.\n"
        f"\n"
        f"## Research Proposal\n"
        f"{proposal_summary}\n"
        f"\n"
        f"## Known Constraints\n"
        f"{constraints_block}\n"
        f"\n"
        f"## Experiment Context\n"
        f"- Scenario: {scenario_name}\n"
        f"- Node ID: {experiment_node_id}\n"
        f"- Workspace: {workspace_ref}\n"
        f"\n"
        f"## Instructions\n"
        f"- `artifact_id`: A unique, descriptive identifier in snake_case (include version, e.g. `my_experiment_v1`).\n"
        f"- `description`: 2-4 sentences explaining what the experiment will do, the key methodology, "
        f"and expected outputs.\n"
        f"- `location`: The output path for artifacts within the workspace.\n"
    )


def feedback_prompt(
    hypothesis_text: str,
    exit_code: int,
    score_text: str,
    logs_summary: str,
    iteration: int,
) -> str:
    return (
        f"You are a research reviewer evaluating experimental results from an automated R&D loop.\n"
        f"\n"
        f"## Experiment (iteration {iteration})\n"
        f"- Hypothesis: {hypothesis_text}\n"
        f"- Exit code: {exit_code}\n"
        f"- Score: {score_text}\n"
        f"\n"
        f"## Execution Logs (truncated)\n"
        f"{logs_summary[:500]}\n"
        f"\n"
        f"## Evaluation Criteria\n"
        f"- exit_code=0 means execution succeeded, but results may still be poor.\n"
        f"- A score of 0.0 on `placeholder_metric` means no real evaluation was run — "
        f"do NOT treat this as a failure. Judge based on the hypothesis and execution quality instead.\n"
        f"- Focus on scientific merit and experimental rigor, not just metrics.\n"
        f"\n"
        f"## Instructions\n"
        f"- `decision`: Should this line of research CONTINUE in the next iteration? (true/false)\n"
        f"- `acceptable`: Did the experiment meet a minimum quality bar? (true/false)\n"
        f"- `reason`: Concise justification for your judgment (1-2 sentences).\n"
        f"- `observations`: Noteworthy patterns, anomalies, or insights from the results.\n"
        f"- `code_change_summary`: What concrete changes would improve the next iteration?\n"
    )
