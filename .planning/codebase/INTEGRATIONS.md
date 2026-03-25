# External Integrations

**Analysis Date:** 2026-03-25

## APIs & External Services

**Agent runtime surfaces:**
- Claude Code runtime roots - repo-local and global installs target `.claude/skills` and `~/.claude/skills`, with a managed runtime bundle under `.claude/rdagent-v3` or `~/.claude/rdagent-v3`; installer logic lives in `v3/devtools/skill_install.py` and the operator workflow is documented in `README.md`.
  - SDK/Client: local filesystem installer in `scripts/install_agent_skills.py` backed by `v3/devtools/skill_install.py`
  - Auth: inherited from the host Claude runtime; no repo-managed env var or token flow found in `v3/` or `scripts/`
- Codex runtime roots - repo-local and global installs target `.codex/skills` and `~/.codex/skills`, with a managed runtime bundle under `.codex/rdagent-v3` or `~/.codex/rdagent-v3`; installer logic lives in `v3/devtools/skill_install.py` and the operator workflow is documented in `README.md`.
  - SDK/Client: local filesystem installer in `scripts/install_agent_skills.py` backed by `v3/devtools/skill_install.py`
  - Auth: inherited from the host Codex runtime; no repo-managed env var or token flow found in `v3/` or `scripts/`

**Python package registry:**
- PyPI - dependencies are resolved through `uv.lock`, which points packages such as `pydantic`, `pytest`, `hypothesis`, `import-linter`, and `ruff` at `https://pypi.org/simple`.
  - SDK/Client: `uv` via `uv sync` in `README.md`, `Makefile`, `scripts/setup_env.sh`, and `.github/workflows/ci.yml`
  - Auth: none detected in repo files; private index configuration was not found

**External execution/evaluation boundaries:**
- Execution engine boundary - the actual engine that starts a run is abstracted behind `ExecutionPort` in `v3/ports/execution.py`; the repo ships the contract, not a concrete remote client.
  - SDK/Client: custom caller-supplied implementation of `ExecutionPort`
  - Auth: caller-owned; no env var or credential handling is implemented in `v3/ports/execution.py`
- Optional embedding/evaluation boundaries - multi-branch sharing and holdout finalization accept injected `EmbeddingPort`, `EvaluationPort`, and `HoldoutSplitPort` implementations through `v3/entry/rd_agent.py`; local defaults are provided in `v3/ports/defaults.py`.
  - SDK/Client: protocol interfaces in `v3/ports/embedding_port.py` and `v3/ports/holdout_port.py`
  - Auth: not handled in-repo; external implementations must supply their own credentials if they call remote services
- Legacy V2 history boundary - historical run/branch reads are abstracted behind `MigrationPort` in `v3/ports/migration.py`, with translators in `v3/compat/v2/translators.py` and `v3/compat/v2/migration_reads.py`.
  - SDK/Client: custom caller-supplied implementation of `MigrationPort`
  - Auth: caller-owned; no credential flow is implemented in the repo

## Data Storage

**Databases:**
- Not detected. The repo persists canonical V3 state as JSON files through `ArtifactStateStore` in `v3/orchestration/artifact_state_store.py` and memory state through `MemoryStateStore` in `v3/orchestration/memory_state_store.py`.
  - Connection: not applicable
  - Client: filesystem-backed implementations of `StateStorePort` and `MemoryStorePort`

**File Storage:**
- Local filesystem only - runs, branches, stages, recovery assessments, DAG nodes/edges, artifacts, memory records, and promotions are written beneath a caller-provided state root in `v3/orchestration/artifact_state_store.py` and `v3/orchestration/memory_state_store.py`.
- Branch workspaces are allocated as filesystem directories and copied/reset with `shutil` in `v3/orchestration/branch_workspace_manager.py`.
- Installed runtime bundles and generated skills are copied or symlinked into `.claude/`, `.codex/`, `~/.claude/`, or `~/.codex/` by `v3/devtools/skill_install.py`.

**Caching:**
- None detected. No Redis, Memcached, or in-repo cache client is declared in `pyproject.toml`, and no cache service integration was found under `v3/` or `scripts/`.

## Authentication & Identity

**Auth Provider:**
- Custom / host-runtime-managed - this repo does not implement login, OAuth, API key loading, or token refresh flows. Operator identity is assumed to come from the external Claude Code or Codex environment that consumes the installed skills described in `README.md`.
  - Implementation: install-time filesystem placement in `v3/devtools/skill_install.py`; runtime calls are local Python function invocations in `v3/entry/` and `v3/tools/`

## Monitoring & Observability

**Error Tracking:**
- None detected. No Sentry, Honeycomb, Datadog, OpenTelemetry, or similar SDK appears in `pyproject.toml`, `uv.lock`, or `v3/`.

**Logs:**
- Console/stdout/stderr only - CLI commands emit JSON or plain-text output in `v3/entry/tool_cli.py`, `scripts/install_agent_skills.py`, and `scripts/bump_version.py`.
- Verification signals come from pytest/import-linter/ruff runs defined in `Makefile`, `scripts/setup_env.sh`, and `.github/workflows/ci.yml`.

## CI/CD & Deployment

**Hosting:**
- Not applicable / no hosted service detected. The repo ships a local standalone runtime bundle and skill set described in `README.md` and built by `v3/devtools/skill_install.py`.

**CI Pipeline:**
- GitHub Actions - the matrix job in `.github/workflows/ci.yml` checks out the repo, sets up Python, installs `uv`, runs `uv sync --extra test --extra lint`, then executes `make lint` and `make test`.

## Environment Configuration

**Required env vars:**
- None detected in repo-owned runtime code. No `os.environ` or `getenv` usage was found under `v3/` or `scripts/`.
- Runtime configuration is carried by CLI arguments and filesystem paths in `scripts/install_agent_skills.py`, `scripts/setup_env.sh`, and `v3/devtools/skill_install.py`.

**Secrets location:**
- Not detected in-repo. No `.env` files were found at the repository root during this audit, and the codebase does not include a secrets loader under `v3/` or `scripts/`.

## Webhooks & Callbacks

**Incoming:**
- None detected. The public surface is local CLI/tool invocation through `v3/entry/tool_cli.py` and Python entrypoints in `v3/entry/`.

**Outgoing:**
- None detected. The repo contains no HTTP client dependency or webhook sender; integration boundaries are Python protocols in `v3/ports/`.

---

*Integration audit: 2026-03-25*
