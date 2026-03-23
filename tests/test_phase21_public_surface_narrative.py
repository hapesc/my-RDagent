from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"


def _readme_text() -> str:
    return README.read_text()


def test_readme_opens_with_start_inspect_continue_mainline() -> None:
    text = _readme_text()

    mainline_index = text.index("## Start -> Inspect -> Continue")
    start_index = text.index("### Start")
    inspect_index = text.index("### Inspect")
    continue_index = text.index("### Continue")

    assert mainline_index < start_index < inspect_index < continue_index


def test_readme_keeps_rd_agent_first_and_balances_multi_branch_with_minimum_path() -> None:
    text = _readme_text()

    assert "Use `rd-agent` first for the default standalone orchestration path." in text
    assert "Start with the recommended multi-branch path when the task benefits from multiple candidate approaches." in text
    assert "For simpler tasks, the strict minimum single-branch start contract from `skills/rd-agent/SKILL.md` is enough." in text


def test_readme_makes_inspect_a_first_class_agent_led_step() -> None:
    text = _readme_text()

    inspect_index = text.index("### Inspect")
    start_index = text.index("### Start")
    tool_catalog_index = text.index("rd-tool-catalog")

    assert "Inspect before continuing when the agent needs to confirm the current state, the correct next surface, or the exact continuation contract." in text
    assert "The agent should inspect current state, identify the next valid step, and present it to the user." in text
    assert "uv run rdagent-v3-tool describe rd_run_start" in text
    assert "cd ~/.codex/rdagent-v3" in text
    assert start_index < inspect_index < tool_catalog_index


def test_readme_explains_installed_runtime_bundle_for_direct_tools() -> None:
    text = _readme_text()

    assert "managed standalone V3 runtime bundle" in text
    assert "./.codex/rdagent-v3" in text
    assert "~/.claude/rdagent-v3" in text
    assert "Direct V3 CLI tools should be called from that installed runtime bundle root" in text


def test_readme_continue_step_routes_to_real_skill_and_tool_surfaces() -> None:
    text = _readme_text()

    assert "skills/rd-propose/SKILL.md" in text
    assert "skills/rd-code/SKILL.md" in text
    assert "skills/rd-execute/SKILL.md" in text
    assert "skills/rd-evaluate/SKILL.md" in text
    assert "skills/rd-tool-catalog/SKILL.md" in text
