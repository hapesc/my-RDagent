# Codebase Conventions

**Analysis Date:** 2026-03-25

## Style Overview

**Overall:** The repository is deliberately contract-first and layer-conscious. Public behavior is encoded through typed snapshots, small orchestration services, and narrow entrypoints rather than ad hoc dict plumbing spread across the tree.

**Core Style Signals:**
- Python modules almost always begin with a one-line module docstring and `from __future__ import annotations`; see `v3/entry/rd_agent.py`, `v3/orchestration/preflight_service.py`, and `v3/contracts/exploration.py`.
- The repo standard is plain Python with strong typing, not metaprogramming-heavy magic. Public state is modeled with Pydantic `BaseModel` classes using `ConfigDict(extra="forbid", frozen=True)` in `v3/contracts/`.
- Enum-like public vocabularies use `StrEnum` so serialized payloads stay stable and human-readable; examples include `StageKey` in `v3/contracts/stage.py` and `ExplorationMode` in `v3/contracts/exploration.py`.
- Formatting expectations are codified in `pyproject.toml`: Ruff targets Python 3.11 and enforces a `line-length = 120`.

## Naming Patterns

**Files and modules:**
- Python files use `snake_case.py`, for example `v3/orchestration/holdout_validation_service.py` and `v3/tools/stage_write_tools.py`.
- Skill packages use hyphenated directory names with a required `SKILL.md`, for example `skills/rd-agent/SKILL.md` and `skills/rd-tool-catalog/SKILL.md`.
- Tests use `tests/test_*.py`, with many files carrying the phase number that introduced or hardened the behavior, such as `tests/test_phase28_integration.py`.

**Functions and constants:**
- Public callable surfaces are consistently prefixed with `rd_`, for example `rd_agent`, `rd_code`, `rd_run_get`, and `rd_stage_complete`.
- Stage entry modules expose `OWNED_STAGE_KEY` and, when applicable, `NEXT_STAGE_KEY`; see `v3/entry/rd_code.py`, `v3/entry/rd_execute.py`, and `v3/entry/rd_propose.py`.
- Internal helpers use a leading underscore for non-exported functions such as `_tool_response`, `_minimum_continuation_skeleton`, and `_primary_blocker`.

**Exports:**
- Many packages define explicit `__all__` lists to mark the intended public surface; examples appear in `v3/entry/__init__.py`, `v3/ports/__init__.py`, and `v3/tools/stage_write_tools.py`.
- Boundary packages sometimes publish a `BOUNDARY_ROLE` constant to make the intended layer explicit; see `v3/entry/__init__.py` and `v3/ports/__init__.py`.

## Architectural Conventions

**Layering:**
- `v3/contracts/` is the stable vocabulary layer and should not depend on orchestration or runtime wiring.
- `v3/ports/` defines replaceable seams such as `StateStorePort`, `ExecutionPort`, `EmbeddingPort`, and `HoldoutSplitPort`.
- `v3/orchestration/` owns stateful behavior and composes contracts, ports, and pure helpers from `v3/algorithms/`.
- `v3/tools/` stays thin: it accepts typed requests, calls one service, and wraps the result into the response envelope.
- `v3/entry/` is the public executable boundary for skills and CLI usage, not the place for deep business logic.

**Legacy isolation:**
- Legacy compatibility is quarantined under `v3/compat/v2/`; current V3 code is expected to avoid direct legacy-runtime imports.
- `.importlinter` enforces this boundary for `v3.entry`, `v3.orchestration`, and `v3.tools`.

**Public response shape:**
- Tool-style entrypoints consistently return a dict with `structuredContent` plus a human-readable `content` array; see `_tool_response` helpers in `v3/entry/rd_code.py` and `v3/tools/stage_write_tools.py`.
- Operator-facing guidance is centralized through `OperatorGuidance` and formatter helpers in `v3/orchestration/operator_guidance.py` rather than handwritten response text in every module.

## Contract and Typing Patterns

**Immutable snapshots:**
- Public state is represented as immutable snapshot objects, for example `RunBoardSnapshot`, `BranchSnapshot`, `StageSnapshot`, and `FinalSubmissionSnapshot`.
- Request/result payloads for direct tools are centralized in `v3/contracts/tool_io.py`, then reused by `v3/tools/` and `v3/entry/tool_catalog.py`.

**Validation style:**
- Fields are constrained at the model layer with `Field(...)` instead of post-hoc checks where possible.
- Cross-field rules live in the contracts layer when they are structural and in services when they are behavioral.

**Protocol-first seams:**
- Replaceable dependencies are expressed as `Protocol`s in `v3/ports/`; concrete implementations are optional and injected from the outside.
- Tests commonly provide deterministic stub implementations instead of mocking random internals.

## State and Persistence Conventions

**Canonical truth:**
- The canonical runtime truth is file-backed JSON persisted through `StateStorePort` and the default `ArtifactStateStore` in `v3/orchestration/artifact_state_store.py`.
- Branch-local workspaces and storage roots are derived through branch isolation helpers rather than hardcoded paths; see `v3/orchestration/branch_isolation_service.py` and `v3/orchestration/branch_workspace_manager.py`.

**ID-oriented modeling:**
- Entities are referenced by stable IDs (`run_id`, `branch_id`, `artifact_id`, `decision_id`, `node_id`) rather than by implicit positional state.
- Decision artifacts are first-class persisted records, not ephemeral logs; see `BranchDecisionSnapshot` in `v3/contracts/exploration.py`.

## Error-Handling Conventions

**Hard invariant failures:**
- Missing or inconsistent canonical state usually raises `KeyError` or `ValueError`; see `v3/orchestration/run_board_service.py`, `v3/orchestration/stage_transition_service.py`, and `v3/orchestration/dag_service.py`.

**Operator-visible blockers:**
- Operator-facing execution blockers are encoded through `PreflightResult` and `OperatorGuidance` instead of silent fallbacks; see `v3/orchestration/preflight_service.py` and all stage entry modules in `v3/entry/`.

**No hidden downgrade path:**
- The codebase generally prefers explicit `blocked`, `review`, `replay`, or `reuse` outcomes over pretending a stage can continue without evidence.

## Testing Conventions

**Isolation-first:**
- Tests usually create a temporary filesystem state root with `tmp_path`, seed `ArtifactStateStore` or `MemoryStateStore`, and exercise public handlers end-to-end.
- Deterministic helper ports are preferred over flaky live dependencies; see the `_DeterministicExecutionPort` pattern reused across `tests/test_phase14_*` and later integration suites.

**Contract locking:**
- Several tests validate documentation or skill contracts directly from disk, not just Python behavior; examples include `tests/test_phase20_stage_skill_contracts.py` and `tests/test_installed_skill_workflows.py`.

---

*Conventions analysis: 2026-03-25*
