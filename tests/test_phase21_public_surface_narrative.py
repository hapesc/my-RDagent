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


def test_readme_keeps_rd_agent_first() -> None:
    text = _readme_text()

    assert "Use `rd-agent` first" in text
    assert "skills/rd-agent/SKILL.md" in text


def test_readme_makes_inspect_a_first_class_step() -> None:
    text = _readme_text()

    inspect_index = text.index("### Inspect")
    start_index = text.index("### Start")

    assert "uv run rdagent-tool describe rd_run_start" in text
    assert "cd ~/.codex/rd-agent" in text
    assert start_index < inspect_index


def test_readme_explains_installed_runtime_bundle_for_direct_tools() -> None:
    text = _readme_text()

    assert "runtime bundle" in text
    assert ".codex/rd-agent" in text
    assert ".claude/rd-agent" in text
    assert "Direct CLI catalog commands should be called from that installed runtime bundle" in text


def test_readme_continue_step_routes_to_stage_skills() -> None:
    text = _readme_text()

    assert "rd-propose" in text
    assert "rd-code" in text
    assert "rd-execute" in text
    assert "rd-evaluate" in text
    assert "rd-tool-catalog" in text
    assert "skills/<name>/SKILL.md" in text or "SKILL.md" in text
