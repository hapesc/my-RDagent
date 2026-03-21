# External Integrations

**Analysis Date:** 2026-03-21

## APIs & External Services

**Agent Runtime Integration:**
- Claude Code and Codex skill runtimes through repo-local skill packages described in `README.md` (see the "Agent Skill Setup" section) and installed via `scripts/install_agent_skills.py` that links/copies `skills/` entries into `.claude/skills` or `.codex/skills` roots.
  - SDK/Client: direct filesystem linkage, no external package.
  - Auth: none beyond local environment access to the target runtime directory set by `--scope` (`local`/`global`).

## Data Storage

**Databases:**
- Not applicable; current surface persists state via the `StateStorePort`/`MemoryStorePort` protocols under `v3/ports` without a bundled DB client, leaving implementation to the runtime environment.

**File Storage:**
- Local filesystem state tracked via `v3.ports.state_store.StateStorePort` and persistent snapshots referenced by `v3.contracts.*` models (`v3.artifact_state_store`, `v3.memory_state_store`) instead of an external service.

**Caching:**
- None detected; branch-level caches live inside `v3.orchestration` services (e.g., `v3.orchestration.branch_board_service`) without a dedicated cache provider.

## Authentication & Identity

**Auth Provider:**
- Custom (none); the repo relies on runtime isolation and makes no authenticated API calls beyond the skills owning their own run inputs.
  - Implementation: CLI arguments feed `StateStorePort` implementations directly (see `v3.entry.rd_agent.rd_agent` signature) with no token exchange.

## Monitoring & Observability

**Error Tracking:**
- None external; text-based errors surfaced via CLI (e.g., `scripts/install_agent_skills.py` prints installation records, `v3.entry.tool_cli` prints JSON errors when lookups fail).

**Logs:**
- Standard output/standard error from CLI modules (see `v3.entry.tool_cli.py` and `scripts/install_agent_skills.py`).

## CI/CD & Deployment

**Hosting:**
- None; repo ships a standalone CLI. Entry points such as `rd-agent` live under `v3.entry` (e.g., `v3.entry.rd_agent.rd_agent`).

**CI Pipeline:**
- `pytest` suites triggered via `uv run python -m pytest ...` commands defined in `README.md`.

## Environment Configuration

**Required env vars:**
- None documented; configuration happens entirely through CLI flags and `pyproject.toml` scripts.

**Secrets location:**
- None stored; install script copies/links skills without secrets, and `.claude/skills`/`.codex/skills` are created under the caller’s home directory.

## Webhooks & Callbacks

**Incoming:**
- None.

**Outgoing:**
- None beyond local CLI dispatches.

---

*Integration audit: 2026-03-21*
