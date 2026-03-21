# Testing Patterns

**Analysis Date:** 2026-03-21

## Test Framework

**Runner:** `pytest>=7.4.0` as defined under `[tool.pytest.ini_options]` in `pyproject.toml:30-35`, with discovery limited to `tests/test_*.py` plus verbose short traceback formatting.

**Assertion Library:** built-in `pytest` assertions paired with dataclass helpers (`tests/test_phase13_v3_tools.py:71-144`).

**Run Commands:** quick verification gates in `README.md:157-169` execute `uv run python -m pytest` with targeted suites, followed by `uv run lint-imports` (via `.importlinter:1-95`) for boundary checks.

## Test File Organization

- Phase-aligned modules live under `tests/` as `test_phase13_*` through `test_phase18_*`, each capturing the semantics of the corresponding iteration (`tests/test_phase13_v3_tools.py:1-644`, `tests/test_phase18_skill_installation.py:22-94`).
- Tool surface and CLI regressions live in `tests/test_v3_tool_cli.py:6-55`, ensuring the catalog entrypoints behave end-to-end.
- The suite mirrors the V3 product layers so changes in `v3.entry`, `v3.orchestration`, or `v3.tools` trigger targeted files rather than one bloated file.

## Test Structure

Most tests follow a deterministic arrange-act-assert pattern: seed `ArtifactStateStore`/`MemoryStateStore`, call the public handler, then assert both `structuredContent` and human-readable `content` text. For example, `tests/test_phase14_skill_agent.py:72-141` starts a single-branch rd-agent flow, writes snapshots, and verifies `result["content"]` contains the expected stage progression messages.

```
# snippet from tests/test_phase14_skill_agent.py:72
state_store = ArtifactStateStore(tmp_path / "state")
run_service = RunBoardService(state_store=state_store, execution_port=_DeterministicExecutionPort())
result = rd_agent(...)
assert result["structuredContent"]["history"][0]["stage_key"] == "framing"
```

State seeds often include helper factories `_branch`, `_artifact`, `_recovery` to keep data realistic (`tests/test_phase13_v3_tools.py:70-333`, `tests/test_phase16_selection.py:16-99`).

## Mocking

`pytest.MonkeyPatch` appears in selection tests to replace the PUCT adapter and observe candidate ordering without hitting the real scheduler (`tests/test_phase16_selection.py:59-127`). Adapters and `ExecutionPort` implementations are swapped with deterministic dataclasses (`tests/test_phase14_execution_policy.py:115-161`).

## Fixtures and Factories

Reusable fixtures include `_DeterministicExecutionPort` dataclasses (e.g., `tests/test_phase14_skill_agent.py:23-69`, `tests/test_phase18_planning_continuity.py:17-63`) and helper constructors like `_branch`/`_artifact` that bundle `StageSnapshot`, `BranchSnapshot`, and `ArtifactSnapshot` objects.

## Coverage

The README’s quick and full gates (`README.md:157-169`) describe the regression targets, while `.importlinter:1-95` keeps architectural constraints in scope. There is no separate coverage command, so focus remains on exercising the documented entrypoints and ensuring `import-linter` enforces module boundaries.

## Test Types

- **Unit tests:** Service-level behaviors for run boards, execution policies, and stage transitions appear across `tests/test_phase14_execution_policy.py:24-195` and `tests/test_phase16_convergence.py:56-125`.
- **Integration tests:** Multi-stage flows in `tests/test_phase16_rd_agent.py:66-237` chain orchestrator services with `StageTransitionService`/`RunBoardService` to validate stop reasons and shared state.
- **E2E tests:** `tests/test_v3_tool_cli.py:6-55` invokes the CLI entrypoint via `capsys` to assert tool listings and error handling, while module-level suites (`tests/test_phase18_skill_installation.py:22-94`) run installer scripts against temporary repositories.

## Common Patterns

- `tmp_path` roots and `ArtifactStateStore`/`MemoryStateStore` ensure filesystem isolation for snapshot persistence (`tests/test_phase16_rd_agent.py:66-237`, `tests/test_phase17_surface_convergence.py:8-124`).
- Tests validate both `structuredContent` (JSON payloads) and narrative `content` text to guard against leaking legacy terminology (`tests/test_phase16_rd_agent.py:163-165`, `tests/test_phase13_v3_tools.py:643-701`).
- Every pipeline test checks that forbidden legacy modules are absent by AST inspection (`tests/test_phase13_v3_tools.py:60-701`), reinforcing `.importlinter` configuration and the requirement that `v3.*` modules never touch `service_contracts` or `app.runtime`.
