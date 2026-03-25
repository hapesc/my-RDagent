from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
PROJECT = REPO_ROOT / ".planning" / "PROJECT.md"
ROADMAP = REPO_ROOT / ".planning" / "ROADMAP.md"


def _requirements_path() -> Path:
    phase17_requirements = REPO_ROOT / ".planning" / "milestones" / "v1.1-REQUIREMENTS.md"
    if phase17_requirements.exists():
        return phase17_requirements

    active_requirements = REPO_ROOT / ".planning" / "REQUIREMENTS.md"
    if active_requirements.exists():
        return active_requirements

    archived_requirements = sorted((REPO_ROOT / ".planning" / "milestones").glob("v*-REQUIREMENTS.md"))
    assert archived_requirements, "expected either an active or archived requirements file"
    return archived_requirements[-1]


def test_surface_requirements_exist_for_phase_17():
    requirements_text = _requirements_path().read_text()

    assert "SURFACE-01" in requirements_text
    assert "SURFACE-02" in requirements_text
    assert "SURFACE-03" in requirements_text


def test_project_and_roadmap_describe_skill_and_cli_surface():
    project_text = PROJECT.read_text()
    roadmap_text = ROADMAP.read_text()

    assert "skill and CLI surface" in project_text or "Skill/CLI-first" in project_text or "Skills and CLI tools" in project_text
    assert "Skills and CLI tools are the product surface" in roadmap_text


def test_readme_describes_skills_plus_cli_tools_surface():
    readme_text = README.read_text()

    assert "skills" in readme_text.lower() and "CLI tool" in readme_text
    assert "install_agent_skills.py" in readme_text
    assert "managed" in readme_text and "runtime bundle" in readme_text
    assert "rd-agent" in readme_text
    assert "## Default Orchestration" in readme_text
    assert "rd-propose" in readme_text
    assert "rd-code" in readme_text
    assert "rd-execute" in readme_text
    assert "rd-evaluate" in readme_text
    assert "## CLI Tool Catalog" in readme_text
    assert "rd-tool-catalog" in readme_text
    assert "uv run rdagent-tool list" in readme_text
    assert "uv run rdagent-tool describe rd_run_start" in readme_text
    assert "## Routing Model" in readme_text
    assert "## Verification" in readme_text
    assert "## Continue This Session" not in readme_text


def test_active_public_surface_docs_do_not_claim_mcp_server_product():
    readme_text = README.read_text()
    project_text = PROJECT.read_text()
    roadmap_text = ROADMAP.read_text()
    requirements_text = _requirements_path().read_text()

    assert "MCP server" not in readme_text
    assert "registry language" not in readme_text
    assert "MCP server" not in project_text
    assert "MCP server" not in roadmap_text
    assert "MCP server" not in requirements_text
