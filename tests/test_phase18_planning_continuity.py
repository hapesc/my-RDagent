from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
STATE = REPO_ROOT / ".planning" / "STATE.md"
HANDOFF = REPO_ROOT / ".planning" / "V3-EXTRACTION-HANDOFF.md"


def test_readme_keeps_public_skills_and_cli_surface() -> None:
    readme_text = README.read_text()

    assert "skills plus CLI tools" in readme_text
    assert "uv run python scripts/install_agent_skills.py --runtime codex --scope local --mode link" in readme_text
    assert "uv run python scripts/install_agent_skills.py --runtime claude --scope global --mode link" in readme_text
    assert "uv run rdagent-v3-tool list" in readme_text
    assert "uv run rdagent-v3-tool describe rd_run_start" in readme_text


def test_readme_no_longer_contains_internal_resume_section() -> None:
    readme_text = README.read_text()

    assert "## Continue This Session" not in readme_text
    assert ".planning/STATE.md" not in readme_text


def test_state_remains_the_canonical_continuity_entrypoint() -> None:
    state_text = STATE.read_text()

    assert "Canonical continuity entrypoint" in state_text
    assert "**Current focus:**" in state_text
    assert "**Next phase:**" in state_text
    assert "Resume file: .planning/STATE.md" in state_text


def test_extraction_handoff_is_historical_only() -> None:
    handoff_text = HANDOFF.read_text()

    assert "status: historical" in handoff_text
    assert "historical extraction evidence" in handoff_text
    assert ".planning/STATE.md" in handoff_text
    assert "docs/context/" not in handoff_text
    assert "/Users/michael-liang/Code/my-RDagent-V3" not in handoff_text
