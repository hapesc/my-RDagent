# Coding Conventions

**Analysis Date:** 2026-03-21

## Naming Patterns

**Files:**
- High-level modules stick to `snake_case` filenames that describe their responsibility, e.g. `v3/orchestration/run_board_service.py` for publishing run/branch truth and `tests/test_phase16_rd_agent.py` for surface-level regression guards (`v3/orchestration/run_board_service.py:30-105`, `tests/test_phase16_rd_agent.py:72-237`).
- The `tests/` suite mirrors production phases with `test_phase13_*` through `test_phase18_*` plus dedicated CLI validation `tests/test_v3_tool_cli.py`, keeping each cross-cutting capability in a distinct file (`tests/test_phase13_v3_tools.py`, `tests/test_phase18_skill_installation.py`, `tests/test_v3_tool_cli.py`).

**Functions:**
- Public helpers follow `snake_case` verbs that describe their action (`v3/entry/rd_agent.py:25-147`, `v3/orchestration/execution_policy.py:36-121`), while tests use the `test_*` prefix so `pytest` can auto-discover them (`tests/test_phase16_selection.py:59-170`).

**Variables:**
- Temporary values, loop indices, and dependency handles stay in `snake_case` (e.g., `current_iteration`, `branch_after`, `stage_after` in `SkillLoopService.run_single_branch`), avoiding single-letter names and keeping intent explicit (`v3/orchestration/skill_loop_service.py:58-235`).

**Types:**
- Pydantic models and enums use `PascalCase` to align with their contract semantics (`RunBoardSnapshot`, `StageSnapshot`, `MemoryRecordSnapshot` in `v3/contracts/run.py:12-62`, `v3/contracts/stage.py:10-44`, `v3/contracts/memory.py:14-82`).

## Code Style

- Every module begins with `from __future__ import annotations` so forward references stay simple and typing stays lightweight (`v3/orchestration/run_board_service.py:3-14`).
- Formatting targets a 120-character line limit via `ruff` (`pyproject.toml:37-46`), while `pytest` files rely on standard indentation and short helper blocks (see `tests/test_phase14_skill_agent.py:72-141`).
- Immutability is enforced through frozen dataclasses and `pydantic` configs: services expose `@dataclass(frozen=True)` wrappers like `RunBoardPublication`/`RunStartPublication`, and contracts use `ConfigDict(extra="forbid", frozen=True)` plus `model_copy` to emit updated snapshots without mutating originals (`v3/orchestration/run_board_service.py:16-103`, `v3/contracts/run.py:38-62`).
- State transitions always create new copies (`model_copy(update=...)`) before writing to the `StateStore`, so no shared mutable structures leak out of the service layer (`v3/orchestration/run_board_service.py:66-103`).

## Import Organization

- Modules import standard library helpers first, third-party packages next, and project-local targets last (e.g., `argparse`, `json`, `sys` precede `v3.*` imports in `v3/entry/tool_cli.py:5-45`).
- The test suite enforces clean imports by parsing ASTs and asserting forbidden legacy modules are absent (`tests/test_phase13_v3_tools.py:60-233`, `tests/test_phase13_v3_tools.py:678-701`).
- `.importlinter` defines the `v3.*` isolation rules so `v3.entry`, `v3.orchestration`, and `v3.tools` never reach legacy modules such as `service_contracts` or `exploration_manager` (`.importlinter:6-95`).

## Error Handling

- Services validate critical inputs early and raise descriptive `KeyError`/`ValueError` messages before proceeding (`v3/orchestration/run_board_service.py:41-103`, `v3/orchestration/branch_lifecycle_service.py:35-140`).
- Tests assert those error signals are reflected in the public payloads or `structuredContent`, e.g., stop reasons and pause messages appear verbatim (`tests/test_phase16_rd_agent.py:75-237`, `tests/test_phase14_execution_policy.py:24-195`).
- Missing stage inputs or workspace resources consistently produce fast failures (`v3/orchestration/skill_loop_service.py:68-141`), keeping the orchestration loop predictable.

## Logging

- Explicit logging frameworks are absent. Instead, modules return structured messages plus `result["content"]` text snippets that describe what happened; regression tests assert text contains key phrases like "advanced to build" and "operator review" (`tests/test_phase14_skill_agent.py:135-140`, `tests/test_phase16_rd_agent.py:135-137`).

## Comments

- Every layer documents its purpose with module-level docstrings and doc comments to explain the public surface (`v3/orchestration/skill_loop_service.py:1-262`, `v3/entry/rd_agent.py:1-150`).
- Tests also include inline verbs describing their scenario (e.g., "runs a multi-branch explore round"), helping future contributors understand why each guard exists (`tests/test_phase16_rd_agent.py:66-137`).

## Function Design

- Services lean on focused helpers such as `_run_stage`/`_ensure_stage_exists` inside `SkillLoopService`, so each function handles one orchestration concept before handing off to the next (`v3/orchestration/skill_loop_service.py:74-236`).
- Entrypoints like `rd_agent` separate CLI argument validation, run start, multi-branch dispatch, and single-branch looping, returning a dict with `structuredContent` plus textual narration (`v3/entry/rd_agent.py:25-147`).

## Module Design

- Public APIs expose a limited `__all__`, keeping only the intended classes/functions visible (`v3/orchestration/run_board_service.py:104-105`).
- Contract modules (e.g., `v3/contracts/run.py`, `v3/contracts/stage.py`, `v3/contracts/memory.py`) focus solely on `pydantic` models/enums with frozen configs and validation helpers, cleanly separating data definitions from behaviors (`v3/contracts/run.py:12-62`, `v3/contracts/stage.py:10-44`, `v3/contracts/memory.py:14-82`).
