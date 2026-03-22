from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

STAGE_SKILLS = {
    "rd-propose": REPO_ROOT / "skills" / "rd-propose" / "SKILL.md",
    "rd-code": REPO_ROOT / "skills" / "rd-code" / "SKILL.md",
    "rd-execute": REPO_ROOT / "skills" / "rd-execute" / "SKILL.md",
    "rd-evaluate": REPO_ROOT / "skills" / "rd-evaluate" / "SKILL.md",
}


def _read_stage_skill(skill_name: str) -> str:
    return STAGE_SKILLS[skill_name].read_text()


def test_stage_skills_share_continuation_skeleton() -> None:
    for text in (_read_stage_skill(skill_name) for skill_name in STAGE_SKILLS):
        assert "## Continue contract" in text
        assert "## Required fields" in text
        assert "## If information is missing" in text
        assert "## Outcome guide" in text
        assert "`run_id`" in text
        assert "`branch_id`" in text
        assert "`summary`" in text
        assert "`artifact_ids`" in text


def test_stage_skills_document_exact_special_fields() -> None:
    execute_text = _read_stage_skill("rd-execute")
    evaluate_text = _read_stage_skill("rd-evaluate")

    assert "`blocking_reasons`" in execute_text
    assert "`recommendation`" in evaluate_text
    assert "`continue`" in evaluate_text
    assert "`stop`" in evaluate_text


def test_stage_skills_require_agent_led_missing_field_handling() -> None:
    for text in (_read_stage_skill(skill_name) for skill_name in STAGE_SKILLS):
        assert "inspect current run or branch state" in text
        assert "surface the exact missing values" in text


def test_stage_skills_point_to_the_next_high_level_action() -> None:
    propose_text = _read_stage_skill("rd-propose")
    code_text = _read_stage_skill("rd-code")
    execute_text = _read_stage_skill("rd-execute")
    evaluate_text = _read_stage_skill("rd-evaluate")

    assert "rd-code" in propose_text
    assert "rd-execute" in code_text
    assert "rd-evaluate" in execute_text or "blocking reasons" in execute_text
    assert "`continue`" in evaluate_text
    assert "`stop`" in evaluate_text
