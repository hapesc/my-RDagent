from __future__ import annotations

from v3.entry.tool_catalog import get_cli_tool, list_cli_tools


def test_tool_catalog_examples_cover_every_tool() -> None:
    tools = list_cli_tools()

    assert tools
    for tool in tools:
        assert tool["examples"]
        first = tool["examples"][0]
        assert first["label"] == "common_path"
        serialized = repr(first["arguments"])
        assert any(
            placeholder in serialized
            for placeholder in ("run-001", "branch-001", "primary", "memory-001")
        )


def test_tool_catalog_routing_guidance_is_explicit() -> None:
    tools = {tool["name"]: tool for tool in list_cli_tools()}

    assert tools["rd_run_start"]["when_to_use"]
    assert tools["rd_run_start"]["when_not_to_use"]
    assert tools["rd_run_start"]["recommended_entrypoint"] == "rd-agent"

    assert tools["rd_branch_fork"]["when_to_use"]
    assert tools["rd_branch_fork"]["when_not_to_use"]
    assert tools["rd_branch_fork"]["recommended_entrypoint"] == "rd-tool-catalog"


def test_list_and_describe_share_operator_guidance_fields() -> None:
    payload = get_cli_tool("rd_run_start")

    assert payload["examples"]
    assert payload["when_to_use"]
    assert payload["when_not_to_use"]
    assert payload["follow_up"]


def test_tool_catalog_follow_up_covers_every_tool() -> None:
    for tool in list_cli_tools():
        assert tool["follow_up"]
        assert tool["follow_up"]["when_successful"]
        assert tool["follow_up"]["next_entrypoint"]
        assert tool["follow_up"]["next_action"]


def test_orchestration_follow_up_points_back_to_rd_agent() -> None:
    tools = {tool["name"]: tool for tool in list_cli_tools()}

    assert tools["rd_run_start"]["follow_up"]["next_entrypoint"] == "rd-agent"
    assert tools["rd_explore_round"]["follow_up"]["next_entrypoint"] == "rd-agent"
    assert tools["rd_converge_round"]["follow_up"]["next_entrypoint"] == "rd-agent"


def test_selection_and_recovery_follow_up_explains_the_next_direct_step() -> None:
    tools = {tool["name"]: tool for tool in list_cli_tools()}

    assert any(
        phrase in tools["rd_branch_select_next"]["follow_up"]["next_action"]
        for phrase in ("rd_branch_get", "rd_stage_get")
    )
    assert "missing evidence" in tools["rd_recovery_assess"]["follow_up"]["next_action"]


def test_stage_oriented_follow_up_uses_shared_skill_vocabulary() -> None:
    tools = {tool["name"]: tool for tool in list_cli_tools()}

    for tool_name in ("rd_run_start", "rd_stage_get", "rd_artifact_list", "rd_recovery_assess", "rd_branch_select_next"):
        next_action = tools[tool_name]["follow_up"]["next_action"]
        assert any(
            skill_name in next_action
            for skill_name in ("rd-propose", "rd-code", "rd-execute", "rd-evaluate")
        )
