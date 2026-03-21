# Technology Stack

**Analysis Date:** 2026-03-21

## Languages

**Primary:**
- Python (>=3.11) - core runtime for all CLI skills and orchestration layers defined under `v3` modules such as `v3.entry`, `v3.orchestration`, and `v3.tools`.

**Secondary:**
- None detected.

## Runtime

**Environment:**
- CPython 3.11+ via `pyproject.toml` requirement (inherited by `pyproject.toml`).

**Package Manager:**
- `pip`/hatchling (build backend configured via `pyproject.toml` → `[build-system]`).
- Lockfile: `uv.lock` governs reproducible installs when `uv sync` is used per README instructions.

## Frameworks

**Core:**
- Custom in-house skill/orchestration layers. Entry modules live at `v3.entry`, `v3.orchestration`, and `v3.tools`, with CLI surfaces defined via `scripts` wrappers and `rd-agent` orchestration skill.

**Testing:**
- `pytest>=7.4.0` (configured via `[tool.pytest.ini_options]`), responsible for suites described in README (`tests/test_*`).

**Build/Dev:**
- `hatchling` build backend (`[build-system]`), `uv` CLI (implied by README commands such as `uv run ...`).

## Key Dependencies

**Critical:**
- `pydantic>=2,<3` - modeling/contraction layer across skills and CLI payload validation inside `v3.contracts`.

**Infrastructure:**
- None beyond standard Python library and `pydantic`; any additional infra dependencies appear transitively through `uv sync`.

## Configuration

**Environment:**
- Entrypoint config defined by `pyproject.toml` scripts (`rdagent-v3-tool` pointing to `v3.entry.tool_cli:main`) and README installer scripts listing `skills/` packages and runtime arguments.

**Build:**
- `pyproject.toml` plus `.importlinter` configuration enforce module boundaries (per workspace layout in README). `uv.lock` ensures reproducible dependency sets for `uv sync`.

## Platform Requirements

**Development:**
- Python 3.11+ runtime, `uv` CLI available, ability to link `skills/` packages into Claude/Codex roots via `scripts/install_agent_skills.py` (see `scripts/install_agent_skills.py`).

**Production:**
- Standalone CLI surface; no hosted server implied. Deploy by installing repo-local skills into a Claude/Codex runtime using `uv run python scripts/install_agent_skills.py ...` and invoking `rd-agent` or `rdagent-v3-tool` as described in `README.md`.

---

*Stack analysis: 2026-03-21*
