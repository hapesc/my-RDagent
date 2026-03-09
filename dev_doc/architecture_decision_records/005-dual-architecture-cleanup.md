# ADR 005: Dual-Architecture Cleanup and Integration

## Status
Accepted (Decided 2026-03-07)

## Context
During the recent development phase, the project had two parallel architecture systems that appeared to be in conflict:
- **System A**: `core/loop/engine.py` and `app/runtime.py` – the working mainline with CLI, API, and UI support.
- **System B**: Multiple top-level service modules (e.g., `planner.py`, `exploration_manager.py`, `memory_service.py`).

Initial analysis suggested System B was a separate, redundant architecture. However, further inspection of `core/loop/engine.py` and `app/runtime.py` revealed that System A actually imports its core data models (e.g., `ExplorationGraph`, `NodeRecord`, `PlanningContext`) from the shared `data_models.py`, and the `LoopEngine` constructor explicitly accepts a `planner`, `exploration_manager`, and `memory_service` as dependencies. The `app/runtime.py:build_runtime()` function is responsible for injecting these System B services into the `LoopEngine`.

## Decision
We decided on a **pragmatic integration** approach:
1.  **Keep System B modules**: Retain them as component stubs to be filled with real implementations, rather than deleting them as redundant.
2.  **Delete dead code**: Remove truly unused files that are not part of either system, such as `main.py`, `demo` files, and the obsolete `orchestrator_rd_loop_engine/` directory.
3.  **No directory restructuring**: Avoid a large-scale reorganization of the project structure at this time, as the dependency injection pattern is already correctly established.

## Consequences
- **Codebase Clarity**: Deleting truly dead code reduces noise and makes it easier for new contributors to understand the project structure.
- **Defined Implementation Targets**: System B modules now serve as clear implementation targets for P0 features, ensuring that development effort is focused on filling existing architectural gaps.
- **Architectural Stability**: By recognizing that System A and System B are already integrated via dependency injection, we avoid the risk of introducing new bugs through unnecessary refactoring.
- **Mainline Support**: The existing CLI, API, and UI in System A remain fully functional and are now the official way to interact with the platform.
- **Forward Path**: Future development should focus on maturing the implementations within the System B component modules while maintaining the injection pattern in `app/runtime.py`.
