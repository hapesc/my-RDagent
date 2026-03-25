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

SHARED_STAGE_CONTRACT = REPO_ROOT / "skills" / "_shared" / "references" / "stage-contract.md"
TOOL_EXECUTION_CONTEXT = REPO_ROOT / "skills" / "_shared" / "references" / "tool-execution-context.md"


def _read_stage_skill(skill_name: str) -> str:
    return STAGE_SKILLS[skill_name].read_text()



def _all_stage_texts() -> list[str]:
    return [_read_stage_skill(skill_name) for skill_name in STAGE_SKILLS]



def _read_continue_workflow(skill_name: str) -> str:
    return STAGE_CONTINUE_WORKFLOWS[skill_name].read_text()



def _read_shared_stage_contract() -> str:
    return SHARED_STAGE_CONTRACT.read_text()



def _read_tool_execution_context() -> str:
    return TOOL_EXECUTION_CONTEXT.read_text()



def _normalized(text: str) -> str:
    return " ".join(text.split())



def _stage_bundle(skill_name: str) -> str:
    return "\n".join(
        [
            _read_stage_skill(skill_name),
            _read_continue_workflow(skill_name),
            _read_shared_stage_contract(),
            _read_tool_execution_context(),
        ]
    )



def test_stage_skills_share_continuation_skeleton() -> None:
    for name in STAGE_SKILLS:
        skill = _normalized(_read_stage_skill(name))
        cont = _normalized(_read_continue_workflow(name))

        assert "<required_fields>" in skill
        assert "run_id" in skill
        assert "branch_id" in skill
        assert "summary" in skill
        assert "artifact_ids" in skill
        assert "<outcome_guide>" in skill

        assert '<step name="validate_fields">' in cont
        assert '<step name="check_stage">' in cont
        assert '<step name="execute_transition">' in cont
        assert '<step name="handoff">' in cont



def test_stage_skills_document_exact_special_fields() -> None:
    execute_skill = _normalized(_read_stage_skill("rd-execute"))
    execute_cont = _normalized(_read_continue_workflow("rd-execute"))
    evaluate_skill = _normalized(_read_stage_skill("rd-evaluate"))
    evaluate_cont = _normalized(_read_continue_workflow("rd-evaluate"))

    assert "blocking_reasons" in execute_skill
    assert "blocking_reasons" in execute_cont
    assert "recommendation" in evaluate_skill
    assert "recommendation" in evaluate_cont
    assert '"continue"' in evaluate_cont
    assert '"stop"' in evaluate_cont



def test_stage_skills_require_agent_led_missing_field_handling() -> None:
    shared = _normalized(_read_shared_stage_contract())

    for name in STAGE_SKILLS:
        cont = _normalized(_read_continue_workflow(name))
        assert "rd_run_get" in cont
        assert "rd_branch_get" in cont
        assert "Derive what can be derived from the response" in cont
        assert "Surface exact missing field names" in cont
        assert "Ask operator ONLY for values that cannot be derived" in cont

    assert "inspect current run or branch state first" in shared
    assert "Surface exact missing field names and any values already recovered." in shared
    assert "Ask the operator only for values that cannot be derived from state." in shared



def test_stage_skills_keep_tool_catalog_as_agent_side_escalation_only() -> None:
    shared_raw = _read_shared_stage_contract()
    shared = _normalized(shared_raw)
    tool_context = _normalized(_read_tool_execution_context())

    for text in _all_stage_texts():
        normalized = _normalized(text)
        assert "@skills/_shared/references/tool-execution-context.md" in normalized
        assert "@skills/_shared/references/stage-contract.md" in normalized

    assert "## When to route to rd-tool-catalog" in shared_raw
    assert "agent-side escalation path" in shared
    assert "manual tool browsing" in shared
    assert "uv run rdagent-v3-tool" in tool_context
    assert "installed standalone V3 runtime bundle root" in tool_context



def test_stage_skills_document_continue_contract_as_paused_run_flow() -> None:
    for name in STAGE_SKILLS:
        skill = _normalized(_read_stage_skill(name))
        cont = _normalized(_read_continue_workflow(name))

        assert "Continue a paused" in cont
        assert "existing V3 run" in cont
        assert "use rd-agent for that" in skill
        assert "current-step" in skill



def test_stage_skills_point_to_the_next_high_level_action() -> None:
    propose_text = _normalized(_read_stage_skill("rd-propose"))
    code_text = _normalized(_read_stage_skill("rd-code"))
    execute_text = _normalized(_read_stage_skill("rd-execute"))
    evaluate_text = _normalized(_read_stage_skill("rd-evaluate"))

    assert "rd-code" in propose_text
    assert "rd-execute" in code_text
    assert "rd-evaluate" in execute_text or "blocking reasons" in execute_text
    assert "continue" in evaluate_text
    assert "stop" in evaluate_text



def test_stage_skills_cover_reuse_review_and_replay_outcomes() -> None:
    for text in _all_stage_texts():
        normalized = _normalized(text)
        assert "reused:" in normalized
        assert "review:" in normalized
        assert "replay:" in normalized



def test_stage_skill_outcome_guides_lock_stage_specific_handoffs() -> None:
    propose_text = _normalized(_read_stage_skill("rd-propose"))
    code_text = _normalized(_read_stage_skill("rd-code"))
    execute_text = _normalized(_read_stage_skill("rd-execute"))
    evaluate_text = _normalized(_read_stage_skill("rd-evaluate"))

    assert "completed: next skill is rd-code" in propose_text
    assert "completed: next skill is rd-execute" in code_text
    assert "completed: next skill is rd-evaluate" in execute_text
    assert "completed with continue: next skill is rd-propose" in evaluate_text
    assert "completed with stop: loop ends, no next stage skill" in evaluate_text
