from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
PROJECT = REPO_ROOT / ".planning" / "PROJECT.md"
ROADMAP = REPO_ROOT / ".planning" / "ROADMAP.md"
REQUIREMENTS = REPO_ROOT / ".planning" / "REQUIREMENTS.md"


def test_surface_requirements_exist_for_phase_17():
    requirements_text = REQUIREMENTS.read_text()

    assert "SURFACE-01" in requirements_text
    assert "SURFACE-02" in requirements_text
    assert "SURFACE-03" in requirements_text


def test_project_and_roadmap_describe_skill_and_cli_surface():
    project_text = PROJECT.read_text()
    roadmap_text = ROADMAP.read_text()

    assert "skill/CLI-first" in project_text
    assert "Skills and CLI tools are the product surface" in roadmap_text
    assert "rdagent-v3-tool" in roadmap_text


def test_readme_exposes_current_cli_and_skill_entrypoints():
    readme_text = README.read_text()

    assert "## CLI Tool Surface" in readme_text
    assert "rdagent-v3-tool list" in readme_text
    assert "rdagent-v3-tool describe rd_run_start" in readme_text
    assert "## Skill Entrypoints" in readme_text
    assert "rd_agent" in readme_text
    assert "rd_propose" in readme_text
    assert "rd_code" in readme_text
    assert "rd_execute" in readme_text
    assert "rd_evaluate" in readme_text
