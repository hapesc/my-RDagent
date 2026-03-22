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
