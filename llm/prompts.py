"""Prompt templates for structured LLM calls.

Each function builds a rich prompt string for a specific pipeline stage.
The LLMAdapter appends JSON schema enforcement separately — these templates
focus on role, context, and evaluation criteria.
"""

from __future__ import annotations

import dataclasses
import json

from llm.codegen import get_few_shot_examples
from llm.schemas import ExperimentDesign, HypothesisModification, PlanningStrategy


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
    previous_proposals: list[str] | None = None,
) -> str:
    history_block = ""
    if previous_proposals:
        items = "\n".join(f"  {i + 1}. {p}" for i, p in enumerate(previous_proposals[-3:]))
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


def planning_strategy_prompt(
    task_summary: str,
    scenario_name: str,
    progress: float,
    stage: str,
    iteration: int,
    history_summary: dict[str, str],
    budget_remaining: float,
) -> str:
    schema_hint = _build_schema_hint(PlanningStrategy)

    history_block = ""
    if history_summary:
        items = "\n".join(f"  - {k}: {v}" for k, v in history_summary.items())
        history_block = f"\n## Exploration History\n{items}\n"

    return (
        f"You are a research strategist planning the next exploration direction in an iterative R&D loop.\n"
        f"\n"
        f"## Task\n"
        f"{task_summary}\n"
        f"\n"
        f"## Context\n"
        f"- Scenario: {scenario_name}\n"
        f"- Iteration: {iteration}\n"
        f"- Progress: {progress:.1%}\n"
        f"- Stage: {stage}\n"
        f"- Budget Remaining: {budget_remaining:.1f} units\n"
        f"{history_block}"
        f"\n"
        f"## Instructions\n"
        f"Choose an exploration strategy for the next phase:\n"
        f"1. Assess current progress and identify bottlenecks.\n"
        f"2. Decide between exploration (trying new approaches) and exploitation (refining current best).\n"
        f"3. Select a method that balances risk and information gain.\n"
        f"4. Justify your selection based on exploration state and remaining budget.\n"
        f"\n"
        f"## Output Fields\n"
        f"- `strategy_name`: Name of the chosen strategy (e.g., 'focused_refinement', 'broad_exploration').\n"
        f"- `method_selection`: Specific method or technique to apply next.\n"
        f"- `exploration_weight`: Weight for exploration vs exploitation (0.0=pure exploit, 1.0=pure explore).\n"
        f"- `reasoning`: Justification for this strategy choice given current progress and budget.\n"
        f"- `budget_allocation`: Optional. Allocate the remaining budget across phases as a JSON object. "
        f'Example: {{"proposal": 120, "coding": 180, "running": 60, "feedback": 60}}\n'
        f"\n"
        f"## Schema\n"
        f"```json\n{schema_hint}\n```"
    )


def coding_prompt(
    proposal_summary: str | None = None,
    constraints: list[str] | None = None,
    experiment_node_id: str | None = None,
    workspace_ref: str | None = None,
    scenario_name: str | None = None,
    scenario_type: str | None = None,
    task_desc: str | None = None,
    workspace: str | None = None,
) -> str:
    constraints_list = constraints or []
    normalized_summary = proposal_summary if proposal_summary is not None else (task_desc or "")
    normalized_node_id = experiment_node_id or "node-unknown"
    normalized_workspace = workspace_ref or workspace or "/tmp/rd_agent_workspace"
    normalized_scenario = scenario_name or scenario_type or "unknown"
    constraints_block = "\n".join(f"  - {c}" for c in constraints_list) if constraints_list else "  (none)"
    scenario_instructions = _coding_scenario_instructions(scenario_name)
    few_shot_block = _render_few_shot_examples(scenario_name)

    base_prompt = (
        f"You are a research engineer translating a proposal into an executable experiment design.\n"
        f"\n"
        f"## Research Proposal\n"
        f"{normalized_summary}\n"
        f"\n"
        f"## Known Risks\n"
        f"{constraints_block}\n"
        f"\n"
        f"## Experiment Context\n"
        f"- Scenario: {normalized_scenario}\n"
        f"- Node ID: {normalized_node_id}\n"
        f"- Workspace: {normalized_workspace}\n"
        f"\n"
        f"## Implementation Rules\n"
        f"- Do not return placeholder, template, TODO, or stub content.\n"
        f"- Be concrete about the exact artifact content and output format.\n"
        f"- Honor the scenario-specific contract below.\n"
        f"\n"
        f"{scenario_instructions}"
        f"\n"
        f"{few_shot_block}"
        f"\n"
        f"## Output Fields\n"
        f"- `artifact_id`: snake_case identifier with version suffix (e.g. `lr_ablation_v2`).\n"
        f"- `artifact`: the complete artifact body. For code scenarios, this must be the full runnable code. "
        f"For structured-text scenarios, this must be the full report markdown.\n"
        f"- `description`: describe the concrete artifact to produce, including what runs, what it measures, "
        f"and what output format or files are produced.\n"
        f"- `location`: Use the workspace path provided above.\n"
    )

    if scenario_type is None:
        return base_prompt

    if scenario_type == "data_science":
        return (
            f"{base_prompt}"
            f"- `code`: Full executable Python program in ONE fenced code block using this exact format:\n"
            f"  ```python\n"
            f"  # executable code here\n"
            f"  ```\n"
            f"\n"
            f"## Data Science Coding Requirements\n"
            f"1. Write runnable Python code, not pseudocode.\n"
            f"2. Read input data from a variable named `data_source` (exact name required).\n"
            f"3. Write evaluation outputs to `metrics.json` and serialize metrics via "
            f"`json.dumps({{'metric': value}})`.\n"
            f"4. Use only safe, standard data-science imports (e.g., pandas, numpy, sklearn, scipy, json, pathlib).\n"
            f"5. Do NOT use TODO, placeholder, or template patterns.\n"
        )

    if scenario_type == "quant":
        return (
            f"{base_prompt}"
            f"- `code`: Python factor-computation implementation in ONE fenced `python` code block, "
            f"including signal construction and metric calculation.\n"
            f"\n"
            f"## Quant Coding Requirements\n"
            f"1. Implement a concrete, executable factor computation pipeline.\n"
            f"2. Include clear input assumptions and produced metrics/output artifacts.\n"
            f"3. Avoid placeholder logic.\n"
        )

    if scenario_type == "synthetic_research":
        return (
            f"{base_prompt}"
            f"\n"
            f"## Synthetic Research Requirements\n"
            f"Provide structured explanatory text only. Do NOT return executable code.\n"
            f"Focus on concise, evidence-oriented research notes and expected findings.\n"
        )

    return base_prompt


def _coding_scenario_instructions(scenario_name: str) -> str:
    scenario_specs = {
        "data_science": (
            "## Scenario Contract\n"
            "- Produce a runnable data-science pipeline description with explicit training and evaluation steps.\n"
            "- The output format must mention `metrics.json` and the evaluation metrics that will be written there.\n"
            "- Put the full runnable Python script in the top-level `artifact` field.\n"
            "- Keep the artifact concise: no narrative comments, no long explanations, no synthetic demo dataset unless required.\n"
            "- Avoid placeholder datasets, fake metrics, and vague references like 'train a model somehow'.\n"
        ),
        "quant": (
            "## Scenario Contract\n"
            "- Produce a factor implementation centered on `compute_factor` with clear input/output expectations.\n"
            "- Respect risk constraints such as forbidden imports, no file I/O, and no network access unless explicitly allowed.\n"
            "- Put the complete factor implementation in the top-level `artifact` field or a fenced Python block.\n"
            "- Describe the returned factor columns and the transformation logic, not a generic template.\n"
        ),
        "synthetic_research": (
            "## Scenario Contract\n"
            "- Produce a structured research artifact with headings, findings, methodology, and conclusion.\n"
            "- Put the complete report markdown in the top-level `artifact` field.\n"
            "- Use the exact headings `## Findings`, `## Methodology`, and `## Conclusion`.\n"
            "- Under `## Findings`, use numbered items like `1.` and `2.` rather than prose paragraphs.\n"
            "- Include quantitative evidence wherever possible instead of generic observations.\n"
            "- Avoid placeholder prose, vague summaries, or restating the task without findings.\n"
        ),
    }
    return scenario_specs.get(
        scenario_name,
        "## Scenario Contract\n- Produce a concrete artifact with no placeholder or template content.\n",
    )


def _render_few_shot_examples(scenario_name: str) -> str:
    examples = get_few_shot_examples(scenario_name)
    if not examples:
        return "## Reference Implementation\nNo curated examples are available for this scenario."

    rendered_examples: list[str] = ["## Reference Implementation"]
    for index, example in enumerate(examples[:2], start=1):
        rendered_examples.extend(
            [
                f"### Example {index}",
                f"Task: {example['task']}",
                f"Artifact type: {example['artifact_type']}",
                "Artifact:",
                "```",
                example["artifact"],
                "```",
            ]
        )
    return "\n".join(rendered_examples) + "\n"


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
    previous_results: list[str],
    current_scores: list[float],
) -> str:
    strategy = _iteration_strategy(iteration)

    previous_block = ""
    if previous_results:
        items = "\n".join(f"  {i + 1}. {result}" for i, result in enumerate(previous_results[-3:]))
        scores_text = ", ".join(f"{s:.3f}" for s in current_scores[-3:]) if current_scores else "N/A"
        previous_block = f"\n## Previous Results\n{items}\nPerformance scores: {scores_text}\n"

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
    candidates: list,
    task_summary: str,
    scenario_name: str,
    evaluation_criteria: str,
) -> str:
    candidates_block = ""
    if candidates:
        items = "\n".join(f"  Candidate {i}: {c.get('summary', '(no summary)')}" for i, c in enumerate(candidates))
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
    trace_summaries: list[str],
    task_summary: str,
    scenario_name: str,
) -> str:
    traces_text = "\n\n".join(f"### Trace {i + 1}\n{summary}" for i, summary in enumerate(trace_summaries))
    schema_hint = _build_schema_hint(ExperimentDesign)
    return (
        f"You are an expert research synthesizer specializing in {scenario_name} experiments.\n\n"
        "## Context\n"
        f"A multi-branch exploration produced {len(trace_summaries)} completed research traces for the task:\n"
        f"**Task**: {task_summary}\n\n"
        "## Completed Traces\n"
        f"{traces_text}\n\n"
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
        f"```json\n{schema_hint}\n```"
    )


def hypothesis_modification_prompt(
    source_hypothesis: str,
    action: str,
    context_items: list[str],
    task_summary: str,
    scenario_name: str,
) -> str:
    schema_hint = _build_schema_hint(HypothesisModification)

    context_block = ""
    if context_items:
        items = "\n".join(f"  - {item}" for item in context_items)
        context_block = f"\n## Context Items\n{items}\n"

    return (
        f"You are a research scientist refining hypotheses in an iterative exploration.\n"
        f"\n"
        f"## Task\n"
        f"{task_summary}\n"
        f"\n"
        f"## Scenario\n"
        f"{scenario_name}\n"
        f"\n"
        f"## Source Hypothesis\n"
        f"{source_hypothesis}\n"
        f"{context_block}"
        f"\n"
        f"## Action\n"
        f"Modify or refine the hypothesis based on: {action}\n"
        f"\n"
        f"## Instructions\n"
        f"Generate a modified version of the hypothesis:\n"
        f"1. Identify the type of modification needed (refinement, pivot, narrowing, broadening).\n"
        f"2. Preserve the core insight if it's still valid.\n"
        f"3. Incorporate lessons from context items.\n"
        f"4. Ensure the modified hypothesis is testable and more specific than the original.\n"
        f"5. Clearly explain the reasoning behind the modification.\n"
        f"\n"
        f"## Output Fields\n"
        f"- `modified_hypothesis`: The refined hypothesis statement (2-3 sentences).\n"
        f"- `modification_type`: Category of change (e.g., 'refinement', 'pivot', 'narrowing').\n"
        f"- `source_hypothesis`: The original hypothesis that was modified (for reference).\n"
        f"- `reasoning`: Explanation of why this modification improves upon the original.\n"
        f"\n"
        f"## Schema\n"
        f"```json\n{schema_hint}\n```"
    )


def structured_feedback_prompt(
    code: str,
    execution_output: str,
    task_description: str,
) -> str:
    """Build prompt for FC-3 three-dimensional structured feedback.

    Generates structured feedback with execution, return_checking, and code dimensions.
    """
    return (
        f"You are a code reviewer evaluating experiment implementation quality.\n"
        f"\n"
        f"## Task Description\n"
        f"{task_description}\n"
        f"\n"
        f"## Submitted Code\n"
        f"```\n{code}\n```\n"
        f"\n"
        f"## Execution Output\n"
        f"{execution_output}\n"
        f"\n"
        f"## Instructions\n"
        f"Evaluate the code along three dimensions:\n"
        f"1. **Execution**: Did the code run correctly? Any runtime errors, crashes, or unexpected behavior?\n"
        f"2. **Return Checking**: Are the returned values and outputs consistent with expectations?\n"
        f"3. **Code Quality**: Is the implementation clean, correct, and aligned with the task?\n"
        f"\n"
        f"## Output Fields\n"
        f"- `execution`: Assessment of execution status and any runtime issues.\n"
        f"- `return_checking`: Assessment of output correctness and consistency.\n"
        f"- `code`: Assessment of code quality, correctness, and alignment with task.\n"
        f"- `final_decision`: true if the implementation is acceptable, false otherwise.\n"
        f"- `reasoning`: Overall reasoning for the decision (1-2 sentences).\n"
    )


def knowledge_extraction_prompt(
    trace_summary: str,
    scenario: str,
) -> str:
    """Build prompt for FC-3 knowledge self-generation.

    Extracts reusable knowledge from a CoSTEER loop trace for storage in memory.
    """
    return (
        f"You are a research scientist extracting reusable knowledge from experiment results.\n"
        f"\n"
        f"## Scenario\n"
        f"{scenario}\n"
        f"\n"
        f"## Experiment Trace Summary\n"
        f"{trace_summary}\n"
        f"\n"
        f"## Instructions\n"
        f"Extract the key lessons and reusable knowledge from this experiment trace:\n"
        f"1. What worked well and should be repeated in similar tasks?\n"
        f"2. What failed and should be avoided?\n"
        f"3. What general principles or patterns emerged?\n"
        f"4. What specific techniques or configurations proved effective?\n"
        f"\n"
        f"## Output Fields\n"
        f"Provide a concise knowledge summary (1-3 sentences) capturing the most "
        f"transferable insight from this experiment. Focus on actionable knowledge "
        f"that would help in future {scenario} experiments.\n"
    )
