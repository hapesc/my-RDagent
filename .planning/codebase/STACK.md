# Technology Stack

**Analysis Date:** 2026-03-25

## Languages

**Primary:**
- Python 3.11+ - the packaged runtime, CLI surface, orchestration services, contracts, and port abstractions all live under `v3/`, with the package requirement declared in `pyproject.toml` and entrypoints implemented in `v3/entry/`.

**Secondary:**
- Bash - repo setup and verification orchestration live in `scripts/setup_env.sh` and are invoked from `Makefile`.
- YAML - CI automation is defined in `.github/workflows/ci.yml`.
- Markdown - operator-facing docs and skill packages live in `README.md` and `skills/*/SKILL.md`.

## Runtime

**Environment:**
- CPython `>=3.11` - declared in `pyproject.toml` under `[project].requires-python`.
- CI proves support on Python 3.11 and 3.12 across `ubuntu-latest` and `macos-latest` in `.github/workflows/ci.yml`.

**Package Manager:**
- `uv` - the repo standard for environment sync and command execution; used in `README.md`, `Makefile`, `.github/workflows/ci.yml`, and `scripts/setup_env.sh`.
- Version: not pinned in-repo; CI installs it through `astral-sh/setup-uv@v4` in `.github/workflows/ci.yml`.
- Lockfile: present as `uv.lock`.

## Frameworks

**Core:**
- Pydantic 2.12.5 - schema and contract validation for tool I/O and snapshots across `v3/contracts/`, `v3/entry/tool_catalog.py`, and `v3/ports/holdout_port.py`; version resolved in `uv.lock`.
- Custom standalone orchestration stack - the public runtime is an in-process skill/CLI architecture built from `v3/entry/`, `v3/orchestration/`, `v3/tools/`, and `v3/ports/` rather than a web framework; see `README.md` and `v3/entry/rd_agent.py`.

**Testing:**
- Pytest 9.0.2 - test runner configured in `pyproject.toml` and used across `tests/test_*.py`; resolved in `uv.lock`.
- Hypothesis 6.151.9 - optional property-based testing dependency declared in `pyproject.toml` and resolved in `uv.lock`.
- Import Linter 2.11 - architectural boundary enforcement configured in `.importlinter`; declared in `pyproject.toml` and resolved in `uv.lock`.

**Build/Dev:**
- Hatchling - build backend declared in `pyproject.toml` under `[build-system]`; exact resolved version is not locked in `uv.lock`.
- Ruff 0.15.7 - linting and formatting tool configured in `pyproject.toml` and used by `Makefile`; resolved in `uv.lock`.
- `argparse`-based CLI - the packaged console command `rdagent-v3-tool` is declared in `pyproject.toml` and implemented in `v3/entry/tool_cli.py`.

## Key Dependencies

**Critical:**
- `pydantic>=2,<3` - the only required runtime dependency in `pyproject.toml`; it underpins immutable models such as `FoldSpec` in `v3/ports/holdout_port.py` and the CLI request/response surface in `v3/contracts/tool_io.py`.
- Python stdlib `json`/`pathlib`/`shutil`/`tomllib` - persistence, installer behavior, and preflight inspection rely heavily on stdlib modules in `v3/orchestration/artifact_state_store.py`, `v3/orchestration/memory_state_store.py`, `v3/devtools/skill_install.py`, and `v3/orchestration/preflight_service.py`.

**Infrastructure:**
- `pytest>=7.4.0` - verify-stage dependency checks and automated tests depend on it; see `pyproject.toml`, `v3/orchestration/preflight_service.py`, and `Makefile`.
- `import-linter>=2.3,<3.0` - dependency gate for module-boundary enforcement; see `.importlinter` and `scripts/setup_env.sh`.
- `ruff>=0.3` - lint and format toolchain for `v3/`, `tests/`, and `scripts/`; see `pyproject.toml` and `Makefile`.

## Configuration

**Environment:**
- The repo is configured by files and CLI flags, not by application env vars. Runtime selection and install scope are controlled by `--runtime`, `--scope`, and `--mode` in `scripts/install_agent_skills.py` and `scripts/setup_env.sh`.
- Install targets are filesystem roots, not service endpoints: local installs write under `.codex/` or `.claude/`, and global installs target `~/.codex/` or `~/.claude/`; see `v3/devtools/skill_install.py`.
- Preflight inspects `pyproject.toml`, Python availability, `uv`, and installed modules before stage continuation; see `v3/orchestration/preflight_service.py`.
- No `.env`-driven configuration was detected during this audit, and no `os.environ`/`getenv` reads were found under `v3/` or `scripts/`.

**Build:**
- Packaging and script metadata live in `pyproject.toml`.
- Reproducible dependency resolution lives in `uv.lock`.
- Lint/test command wrappers live in `Makefile`.
- Import boundary rules live in `.importlinter`.
- CI automation lives in `.github/workflows/ci.yml`.

## Platform Requirements

**Development:**
- Python 3.11+ and `uv` are required to run `uv sync --extra test`, `uv run python -m pytest`, and `uv run rdagent-v3-tool ...`; see `README.md`, `Makefile`, and `scripts/setup_env.sh`.
- Developers need filesystem access to the target agent runtime roots because installer flows create managed bundles and skills under `.codex/`, `.claude/`, `~/.codex/`, or `~/.claude/`; see `v3/devtools/skill_install.py`.
- The repo assumes a POSIX-like shell for setup automation because `scripts/setup_env.sh` uses Bash.

**Production:**
- The shipped artifact is a standalone local runtime bundle plus skills, not a hosted server. The canonical operator surface is the installed skill packages under `skills/` and the console script `rdagent-v3-tool`; see `README.md`, `pyproject.toml`, and `v3/entry/tool_cli.py`.
- Runtime state is persisted on the local filesystem as JSON snapshots rather than in a managed database; see `v3/orchestration/artifact_state_store.py` and `v3/orchestration/memory_state_store.py`.

---

*Stack analysis: 2026-03-25*
