from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

STAGE_SKILLS = {
    "rd-propose": REPO_ROOT / "skills" / "rd-propose" / "SKILL.md",
    "rd-code": REPO_ROOT / "skills" / "rd-code" / "SKILL.md",
    "rd-execute": REPO_ROOT / "skills" / "rd-execute" / "SKILL.md",
    "rd-evaluate": REPO_ROOT / "skills" / "rd-evaluate" / "SKILL.md",
}

STAGE_CONTINUE_WORKFLOWS = {
    "rd-propose": REPO_ROOT / "skills" / "rd-propose" / "workflows" / "continue.md",
    "rd-code": REPO_ROOT / "skills" / "rd-code" / "workflows" / "continue.md",
    "rd-execute": REPO_ROOT / "skills" / "rd-execute" / "workflows" / "continue.md",
    "rd-evaluate": REPO_ROOT / "skills" / "rd-evaluate" / "workflows" / "continue.md",
}


def _read_stage_skill(skill_name: str) -> str:
    return STAGE_SKILLS[skill_name].read_text()


def _all_stage_texts() -> list[str]:
    return [_read_stage_skill(skill_name) for skill_name in STAGE_SKILLS]


def _read_continue_workflow(skill_name: str) -> str:
    return STAGE_CONTINUE_WORKFLOWS[skill_name].read_text()


def _all_continue_texts() -> list[str]:
    return [_read_continue_workflow(name) for name in STAGE_CONTINUE_WORKFLOWS]


def _continuation_text(skill_name: str) -> str:
    """Read continuation contract from workflows/continue.md if it exists, else SKILL.md."""
    wf = STAGE_CONTINUE_WORKFLOWS[skill_name]
    if wf.is_file():
        return wf.read_text()
    return _read_stage_skill(skill_name)


def test_stage_skills_share_continuation_skeleton() -> None:
    for name in STAGE_SKILLS:
        cont = _continuation_text(name)
        assert "## Required fields" in cont
        assert "## If information is missing" in cont
        assert "`run_id`" in cont
        assert "`branch_id`" in cont
        assert "`summary`" in cont
        assert "`artifact_ids`" in cont
        # Outcome guide always stays in SKILL.md
        skill = _read_stage_skill(name)
        assert "## Outcome guide" in skill


def test_stage_skills_document_exact_special_fields() -> None:
    execute_cont = _continuation_text("rd-execute")
    evaluate_cont = _continuation_text("rd-evaluate")

    assert "`blocking_reasons`" in execute_cont
    assert "`recommendation`" in evaluate_cont
    assert "`continue`" in evaluate_cont
    assert "`stop`" in evaluate_cont


def test_stage_skills_require_agent_led_missing_field_handling() -> None:
    for name in STAGE_SKILLS:
        cont = _continuation_text(name)
        assert "inspect current run or branch state" in cont
        assert "surface the exact missing values" in cont
        assert "Ask the operator only for values that cannot already be derived" in cont


def test_stage_skills_keep_tool_catalog_as_agent_side_escalation_only() -> None:
    for text in _all_stage_texts():
        assert "## Tool execution context" in text
        assert "uv run rdagent-v3-tool" in text
        assert "installed standalone V3 runtime bundle root" in text
        assert "## When to route to rd-tool-catalog" in text
        assert "agent-side escalation path" in text
        assert "browse tools manually" in text or "manual tool browsing" in text


def test_stage_skills_document_continue_contract_as_paused_run_flow() -> None:
    for name in STAGE_SKILLS:
        cont = _continuation_text(name)
        assert "continue a paused run" in cont
        assert "rather than restarting" in cont or "not to restart" in cont
        assert "current-step" in cont


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


def test_stage_skills_cover_reuse_review_and_replay_outcomes() -> None:
    for text in _all_stage_texts():
        assert "`reused`" in text
        assert "`review`" in text
        assert "`replay`" in text


def test_stage_skill_outcome_guides_lock_stage_specific_handoffs() -> None:
    propose_text = _read_stage_skill("rd-propose")
    code_text = _read_stage_skill("rd-code")
    execute_text = _read_stage_skill("rd-execute")
    evaluate_text = _read_stage_skill("rd-evaluate")

    assert "the next high-level action is `rd-code`" in propose_text
    assert "the next high-level action is `rd-execute`" in code_text
    assert "the next high-level action is `rd-evaluate`" in execute_text
    assert "the next high-level action is `rd-propose`" in evaluate_text
    assert "stop the loop" in evaluate_text
