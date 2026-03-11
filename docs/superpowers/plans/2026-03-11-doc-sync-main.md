# Main Branch Doc Sync Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update repository documentation so it matches the current `main` branch runtime, CLI/API surface, and deployment constraints.

**Architecture:** This is a documentation-only sync pass driven by code reality. The work starts from executable entrypoints (`agentrd_cli.py`, `cli.py`, `app/runtime.py`, `app/control_plane.py`, `app/config.py`) and then rewrites the docs that currently contradict them, especially around LLM provider requirements, configuration defaults, Docker workflows, and self-correction behavior.

**Tech Stack:** Markdown docs, Python CLI/runtime, FastAPI control plane, uv, Docker Compose

---

### Task 1: Sync top-level user docs

**Files:**
- Modify: `README.md`
- Modify: `QUICKSTART.md`

- [ ] Rewrite setup and quickstart instructions to use commands that actually exist.
- [ ] Remove or correct claims about runtime mock fallback where code now requires a real provider for actual runs.
- [ ] Ensure CLI examples match `agentrd_cli.py` and `cli.py` flags.

### Task 2: Sync operational docs

**Files:**
- Modify: `dev_doc/configuration.md`
- Modify: `dev_doc/runbook.md`
- Modify: `dev_doc/deployment.md`
- Modify: `dev_doc/api_reference.md`

- [ ] Align config defaults and environment-variable mappings with `app/config.py`.
- [ ] Align health, startup, and control-plane behavior with `app/control_plane.py`.
- [ ] Remove deployment smoke steps that rely on non-existent runtime mock behavior.

### Task 3: Sync design and security docs

**Files:**
- Modify: `dev_doc/architecture.md`
- Modify: `docs/design/agent-loop-self-correction.md`
- Modify: `SECURITY.md`

- [ ] Update architectural status text so it reflects what is implemented today instead of stale draft wording.
- [ ] Rewrite self-correction design notes to describe the current code path, including what is implemented versus what remains planned.
- [ ] Remove references to unsupported secret-management files and keep security guidance aligned with repo contents.

### Task 4: Verify documentation against executable behavior

**Files:**
- Review only

- [ ] Run the current startup and CLI help commands to validate documented entrypoints.
- [ ] Inspect final diffs to ensure only documentation and doc-like support files changed.
