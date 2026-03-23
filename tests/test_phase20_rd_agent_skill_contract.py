from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RD_AGENT_SKILL = REPO_ROOT / "skills" / "rd-agent" / "SKILL.md"
RD_AGENT_DIR = REPO_ROOT / "skills" / "rd-agent"
RD_AGENT_START_CONTRACT = RD_AGENT_DIR / "workflows" / "start-contract.md"
RD_AGENT_FAILURE_ROUTING = RD_AGENT_DIR / "references" / "failure-routing.md"


def _skill_text() -> str:
    return RD_AGENT_SKILL.read_text()


def test_rd_agent_skill_names_minimum_start_contract() -> None:
    text = _skill_text()

    assert "## Required fields" in text
    assert "## Optional fields" in text
    assert "`title`" in text
    assert "`task_summary`" in text
    assert "`scenario_label`" in text
    assert "`stage_inputs.framing.summary`" in text
    assert "`stage_inputs.framing.artifact_ids`" in text


def test_rd_agent_skill_separates_minimum_and_recommended_paths() -> None:
    text = RD_AGENT_START_CONTRACT.read_text()

    assert "## Minimum start contract" in text
    assert "## Recommended multi-branch contract" in text
    assert "`branch_hypotheses`" in text
    assert "it is not part of the strict minimum start contract" in text
    assert "the first internal step is `framing`" in text


def test_rd_agent_skill_keeps_required_and_optional_field_layers_distinct() -> None:
    text = _skill_text()

    required_start = text.index("## Required fields")
    optional_start = text.index("## Optional fields")

    assert required_start < optional_start
    assert "`initial_branch_label`" in text
    assert "`execution_mode`" in text
    assert "`max_stage_iterations`" in text


def test_rd_agent_skill_explains_default_pause_behavior_in_plain_language() -> None:
    text = RD_AGENT_START_CONTRACT.read_text()

    assert "## Default stop behavior" in text
    assert "`gated + max_stage_iterations=1`" in text
    assert "complete the current step, then pause for human review before continuing" in text
    assert "the next step is prepared but is not continued automatically" in text
    assert "`awaiting_operator`" in text
    assert "one step finishes, the following step is queued up" in text


def test_rd_agent_skill_keeps_tool_catalog_as_agent_side_escalation() -> None:
    text = _skill_text()

    assert "## Tool execution context" in text
    assert "uv run rdagent-v3-tool" in text
    assert "installed standalone V3 runtime bundle root" in text
    assert "do not search other repos or `HOME`" in text
    assert "## When to route to rd-tool-catalog" in text
    assert "agent needs a concrete direct tool in the background" in text
    assert "Do not push the operator into manual tool selection" in text
    assert "agent-side escalation path" in text


def test_rd_agent_skill_requires_agent_led_missing_field_recovery() -> None:
    text = RD_AGENT_FAILURE_ROUTING.read_text()

    assert "## If information is missing" in text
    assert "inspect current run or branch state" in text
    assert "surface the exact missing values" in text
    assert "Only ask the operator for values that cannot already be derived" in text


def test_rd_agent_skill_ends_with_explicit_success_contract() -> None:
    text = _skill_text()

    assert "## Success contract" in text
    assert "starts the run or advances the high-level loop" in text
    assert "route to a stage skill or to `rd-tool-catalog`" in text
