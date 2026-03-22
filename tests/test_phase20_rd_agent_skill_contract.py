from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RD_AGENT_SKILL = REPO_ROOT / "skills" / "rd-agent" / "SKILL.md"


def _skill_text() -> str:
    return RD_AGENT_SKILL.read_text()


def test_rd_agent_skill_names_minimum_start_contract() -> None:
    text = _skill_text()

    assert "`title`" in text
    assert "`task_summary`" in text
    assert "`scenario_label`" in text
    assert "`stage_inputs.framing.summary`" in text
    assert "`stage_inputs.framing.artifact_ids`" in text


def test_rd_agent_skill_separates_minimum_and_recommended_paths() -> None:
    text = _skill_text()

    assert "## Minimum start contract" in text
    assert "## Recommended multi-branch contract" in text
    assert "`branch_hypotheses`" in text


def test_rd_agent_skill_explains_default_pause_behavior_in_plain_language() -> None:
    text = _skill_text()

    assert "`gated + max_stage_iterations=1`" in text
    assert "complete the current step, then pause for human review before continuing" in text
    assert "the next step is prepared but is not continued automatically" in text
    assert "`awaiting_operator`" in text


def test_rd_agent_skill_requires_agent_led_missing_field_recovery() -> None:
    text = _skill_text()

    assert "inspect current run or branch state" in text
    assert "surface the exact missing values" in text
