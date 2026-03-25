from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
HANDOFF = REPO_ROOT / ".planning" / "V3-EXTRACTION-HANDOFF.md"
STATE = REPO_ROOT / ".planning" / "STATE.md"


def test_readme_keeps_public_skills_and_cli_surface() -> None:
    readme_text = README.read_text()

    assert "skills" in readme_text.lower() and "CLI tool" in readme_text
    assert "install_agent_skills.py" in readme_text
    assert "runtime bundle" in readme_text
    assert "uv run rdagent-tool list" in readme_text
    assert "uv run rdagent-tool describe rd_run_start" in readme_text


def test_readme_no_longer_contains_internal_resume_section() -> None:
    readme_text = README.read_text()

    assert "## Continue This Session" not in readme_text
    assert ".planning/STATE.md" not in readme_text


def test_state_remains_the_canonical_continuity_entrypoint() -> None:
    state_text = STATE.read_text()

    assert "Canonical continuity entrypoint" in state_text
    assert "**Canonical continuity entrypoint:** `.planning/STATE.md`" in state_text
    # When between milestones, these fields may not be present
    has_active_milestone = "milestone: none" not in state_text
    if has_active_milestone:
        assert "**Current focus:**" in state_text
        assert "**Next phase:**" in state_text
        assert "Resume file: .planning/" in state_text


def test_extraction_handoff_is_historical_only() -> None:
    handoff_text = HANDOFF.read_text()

    assert "status: historical" in handoff_text
    assert "historical extraction evidence" in handoff_text
    assert ".planning/STATE.md" in handoff_text
    assert "docs/context/" not in handoff_text
