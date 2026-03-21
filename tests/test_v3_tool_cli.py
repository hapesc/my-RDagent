from __future__ import annotations

import json


def test_v3_tool_cli_lists_catalog(capsys) -> None:
    from v3.entry.tool_cli import main

    exit_code = main(["list"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert {tool["name"] for tool in payload} >= {"rd_run_start", "rd_explore_round", "rd_converge_round"}
    assert all(tool["surface"] == "cli_tool" for tool in payload)


def test_v3_tool_cli_describes_single_tool(capsys) -> None:
    from v3.entry.tool_cli import main

    exit_code = main(["describe", "rd_run_start"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["name"] == "rd_run_start"
    assert payload["surface"] == "cli_tool"
    assert payload["command"] == "rdagent-v3-tool describe rd_run_start"
    assert payload["inputSchema"]["title"] == "RunStartRequest"


def test_v3_tool_cli_rejects_unknown_tool(capsys) -> None:
    from v3.entry.tool_cli import main

    exit_code = main(["describe", "missing-tool"])
    captured = capsys.readouterr()
    payload = json.loads(captured.err)

    assert exit_code == 3
    assert "tool not found" in payload["error"]
