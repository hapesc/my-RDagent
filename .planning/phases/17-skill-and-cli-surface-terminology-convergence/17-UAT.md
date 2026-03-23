---
status: complete
phase: 17-skill-and-cli-surface-terminology-convergence
source: 17-01-SUMMARY.md, 17-02-SUMMARY.md, 17-03-SUMMARY.md
started: 2026-03-21T10:28:01Z
updated: 2026-03-21T12:04:05Z
---

## Current Test

[testing complete]

## Tests

### 1. README public surface narrative
expected: Open `README.md`. It should present `rd-agent` as the default orchestration entrypoint first, then the stage skills `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate`, and then `rd-tool-catalog` plus `rdagent-v3-tool list` / `describe` as the selective downshift layer for direct tools.
result: pass

### 2. CLI tool catalog routing metadata
expected: Run `rdagent-v3-tool list` and `rdagent-v3-tool describe rd_run_start`. The JSON output should expose routing metadata such as `category`, `subcategory`, and `recommended_entrypoint`, and orchestration tools should point back to `rd-agent`.
result: pass

### 3. Skill package routing boundaries
expected: Open the `skills/rd-*` packages. Each public skill should clearly say when to use it, when to route to `rd-tool-catalog`, and when not to use it, so the repo-local skill surface is real rather than docs-only.
result: pass

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0

## Gaps

<!-- none yet -->
