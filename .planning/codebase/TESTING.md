# Testing Patterns

**Analysis Date:** 2026-03-25

## Test Framework

**Primary runner:**
- `pytest` is the canonical test runner, configured in `pyproject.toml` under `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `python_files = "test_*.py"`, and verbose short tracebacks.

**Supporting verification tools:**
- `hypothesis` is available as an optional test dependency in `pyproject.toml`, though the current suite is still dominated by deterministic example-based tests.
- `import-linter` is part of the test extra and enforces architectural boundaries from `.importlinter`.
- Ruff is used separately for lint/format verification through `make lint`, not as a pytest plugin.

**Primary commands:**
- `make test` runs `uv run python -m pytest tests/ -q`.
- `make lint` runs `uv run ruff check v3/ tests/ scripts/`.
- `make verify` composes lint plus the full pytest suite.
- `scripts/setup_env.sh` offers a smaller quick gate and a wider full gate for install/setup validation.

## Test Suite Organization

**Top-level layout:**
- The suite lives entirely under `tests/`.
- Files are organized mostly by phase/regression slice rather than by Python package, which mirrors how the repository evolved and makes it obvious which shipped milestone a test protects.

**Current coverage bands:**
- Baseline tool and stage behavior: `tests/test_phase13_v3_tools.py`, `tests/test_phase14_stage_skills.py`, `tests/test_phase14_execution_policy.py`
- Memory, isolation, and selection: `tests/test_phase15_*`, `tests/test_phase16_*`
- Public-surface and documentation contracts: `tests/test_phase18_planning_continuity.py`, `tests/test_phase20_rd_agent_skill_contract.py`, `tests/test_phase20_stage_skill_contracts.py`, `tests/test_phase21_public_surface_narrative.py`
- Preflight and operator guidance: `tests/test_phase22_intent_routing.py`, `tests/test_phase23_*`, `tests/test_phase24_*`, `tests/test_phase25_*`
- Multi-branch graph, pruning, merge, sharing, and finalization: `tests/test_phase26_*`, `tests/test_phase27_*`, `tests/test_phase28_*`, `tests/test_phase29_entry_wiring.py`, `tests/test_phase31_*`
- CLI contract coverage: `tests/test_v3_tool_cli.py`
- Installed-skill workflow validation: `tests/test_installed_skill_workflows.py`

## Test Structure

**Typical pattern:**
- Build a temporary state root with `tmp_path`
- Seed `ArtifactStateStore` or `MemoryStateStore`
- Compose the minimal services needed for the public handler
- Call the public function (`rd_agent`, `rd_code`, `rd_stage_complete`, `rd_branch_select_next`, etc.)
- Assert both machine payloads and operator-facing text

**Representative examples:**
- `tests/test_phase14_skill_agent.py` and `tests/test_phase16_rd_agent.py` drive end-to-end orchestration using deterministic execution ports.
- `tests/test_phase24_operator_guidance.py` and `tests/test_phase24_stage_next_step_guidance.py` lock the exact public wording and routing shape of operator guidance.
- `tests/test_phase20_stage_skill_contracts.py` and `tests/test_installed_skill_workflows.py` treat skill docs and installed workflow files as testable artifacts, not informal prose.
- `tests/test_phase28_integration.py` and `tests/test_phase31_integration.py` cover DAG/finalization and graceful-degradation paths across multiple collaborating services.

## Mocking and Fakes

**Preferred strategy:**
- The codebase favors deterministic fake ports or tiny helper classes over broad monkeypatching of internal implementation details.

**Common doubles:**
- `_DeterministicExecutionPort` patterns appear throughout the phase 14/16 tests to keep run startup predictable.
- Stub holdout ports such as `StubEvaluationPort` and `StubHoldoutSplitPort` from `v3/ports/holdout_port.py` are used in finalization tests.
- `pytest.MonkeyPatch` is used selectively when the test needs to observe adapter wiring or override one narrow behavior, for example in `tests/test_phase16_selection.py`, `tests/test_phase26_dag_service.py`, and `tests/test_phase31_integration.py`.
- `unittest.mock.MagicMock` appears in newer integration tests where the dependency is intentionally optional or only a small subset of behavior matters.

## What the Suite Protects Well

**Public contracts:**
- The repository is unusually strong at locking public shape. Tests cover CLI list/describe output, stage-entry payloads, operator-guidance wording, skill-document requirements, and installed workflow artifacts.

**State transitions:**
- Stage completion, replay, blocking, reuse/review decisions, and next-stage materialization are all covered by focused regression files such as `tests/test_phase14_stage_skills.py`, `tests/test_phase25_stage_materialization.py`, and `tests/test_phase25_outcome_consistency.py`.

**Multi-branch flow:**
- Branch selection, pruning, sharing, DAG topology, complementarity, and holdout-backed finalization are all exercised across `tests/test_phase26_*`, `tests/test_phase27_*`, and `tests/test_phase28_*`.

**Wiring regressions:**
- `tests/test_phase29_entry_wiring.py`, `tests/test_phase31_tools.py`, and `tests/test_phase31_integration.py` protect the high-risk service wiring and graceful-degradation paths added in later milestones.

## CI and Local Verification

**CI matrix:**
- `.github/workflows/ci.yml` runs on `ubuntu-latest` and `macos-latest` with Python 3.11 and 3.12.
- CI installs dependencies with `uv sync --extra test --extra lint`, then runs `make lint` and `make test`.

**Local developer flow:**
- `Makefile` is the simplest local interface for lint/test/verify.
- `scripts/setup_env.sh` adds install-flow validation because the repo’s public surface is not just Python modules, but also generated skill/runtime bundles under `.claude/` and `.codex/`.

## Notable Gaps

**No coverage metric in the default workflow:**
- The repo does not currently run `coverage.py` or publish a coverage threshold. Confidence comes from focused regression breadth rather than a numeric coverage gate.

**No concurrency or stress testing:**
- The filesystem-backed stores and workspace manager are exercised functionally, but there is no dedicated suite for concurrent writers, large state trees, or repeated branch-fork churn.

**No real external backend tests:**
- External seams such as `ExecutionPort`, `EmbeddingPort`, and holdout evaluation are mostly validated through stubs/fakes, not through live integrations.

**No Windows CI lane:**
- CI currently covers macOS and Linux only. Given the Bash-heavy setup flow and filesystem-oriented installer behavior, Windows-specific issues would not be caught automatically.

---

*Testing analysis: 2026-03-25*
