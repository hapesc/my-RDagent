# LangSmith Benchmark Mapping Design

Date: 2026-03-13

## Summary

This design maps the existing `2026-03-13-v2-langsmith-benchmark-refactor.md` plan onto the current repository structure, which does not contain a `v2/` package. The implementation keeps the plan's architecture and migration intent intact while relocating responsibilities into new top-level `benchmarking/` and `tracing/` packages and integrating them with the current `app/`, `core/`, `trace_store/`, `evaluation_service/`, and `tests/` layout.

## Goals

- Make the new benchmark stack LangSmith-first.
- Make the new benchmark stack the primary benchmark mainline.
- Keep the existing runtime in `app/` and `core/`, but expose stable integration points for benchmark execution and tracing.
- Use `MLE-bench` as the `data_science` scenario-native evaluator.
- Use `QuantEval` as the `quant` scenario-native evaluator.
- Demote DeepEval-based evaluation and `tests/evals/` to legacy migration coverage.

## Non-Goals

- Rebuild the runtime under a new `v2/` namespace.
- Preserve DeepEval as a required dependency for benchmark-critical paths.
- Move new benchmark logic into `evaluation_service/`.

## Repository Mapping

The original plan assumes these target paths:

- `v2/benchmark/*`
- `v2/tracing/*`
- `v2/runtime.py`
- `v2/run_service.py`
- `v2/storage/event_log.py`
- `tests/v2/*`

The current repository contains:

- `app/runtime.py`
- `core/loop/run_service.py`
- `trace_store/service.py`
- `evaluation_service/*`
- `tests/*`
- `tests/evals/*`
- `tests/golden_tasks/*`

The mapped target layout is:

- `benchmarking/contracts.py`
- `benchmarking/result_schema.py`
- `benchmarking/profiles.py`
- `benchmarking/task_registry.py`
- `benchmarking/runner.py`
- `benchmarking/reporting.py`
- `benchmarking/langsmith_backend.py`
- `benchmarking/adapters/mlebench_adapter.py`
- `benchmarking/adapters/quanteval_adapter.py`
- `benchmarking/evaluators/criteria.py`
- `benchmarking/evaluators/judge.py`
- `benchmarking/evaluators/rules.py`
- `tracing/config.py`
- `tracing/recorder.py`
- `tracing/sinks.py`
- benchmark tests under `tests/benchmarking/*`
- runtime integration tests added to existing runtime/run service suites or new focused integration files under `tests/`

## Architecture

### Benchmarking Package

`benchmarking/` becomes the authoritative benchmark feature path.

Responsibilities:

- define benchmark contracts and normalized result schemas
- define benchmark profiles and task sources
- run benchmark cases against the current runtime
- evaluate structural rules, scenario-native scores, and judge scores
- report results locally and optionally upload to LangSmith

`benchmarking/` must not depend on DeepEval.

### Tracing Package

`tracing/` becomes the benchmark-aware tracing integration path.

Responsibilities:

- load tracing configuration
- construct benchmark metadata
- expose recorder hooks callable from the runtime
- send traces to LangSmith as the primary sink
- optionally mirror traces to local JSONL storage

### Runtime Integration

The runtime remains in the existing application stack:

- `app/runtime.py` continues to assemble the runtime
- `core/loop/run_service.py` continues to manage run lifecycle

Required additions:

- runtime context carries tracing configuration and provider/model metadata
- run service accepts an optional recorder
- run service exposes an explicit benchmark-consumable result payload

The benchmark runner must consume the explicit payload rather than scrape internals.

### Trace Storage Migration

`trace_store/service.py` currently acts as append-only JSONL trace storage. Under the new design it is no longer the benchmark system of record. Instead:

- LangSmith is the primary trace sink for benchmark runs
- local JSONL becomes an optional mirror/export sink
- benchmark reporting must not require reading JSONL files directly

## Data Flow

1. Benchmark CLI parses `profile`, `scenario`, `output-dir`, comparison flags, and upload flags.
2. `benchmarking.runner` resolves the profile and materializes tasks from `benchmarking.task_registry`.
3. Each benchmark task executes against a runtime target adapter backed by `app/runtime.py` and `core/loop/run_service.py`.
4. `core/loop/run_service.py` emits node-boundary recorder events through `tracing.recorder`.
5. `tracing.sinks` routes events to LangSmith and optional JSONL mirror storage.
6. `core/loop/run_service.py` returns or exposes a stable structured result payload.
7. `benchmarking.runner` applies:
   - structural rules
   - scenario-native evaluation via adapters
   - judge evaluators
8. `benchmarking.reporting` writes normalized JSON and Markdown summaries.
9. `benchmarking.langsmith_backend` handles dataset binding, experiment launch, evaluator registration, and summary metadata.

## Module Boundaries

### `app/runtime.py`

Owns:

- tracing config injection
- real provider construction and exposure of provider/model identity
- preservation of existing runtime assembly responsibilities

Must not own:

- benchmark case orchestration
- benchmark evaluator logic
- benchmark result reporting

### `core/loop/run_service.py`

Owns:

- lifecycle control
- pause/resume/fork behavior
- recorder callbacks at node boundaries
- benchmark payload exposure for completed runs

Must not own:

- benchmark scoring logic
- scenario-native grading logic
- LangSmith dataset/experiment orchestration

### `evaluation_service/`

Owns during migration:

- existing runtime evaluation behavior that the loop still depends on
- legacy DeepEval metric implementations as migration input material

Must not own going forward:

- new benchmark features
- LangSmith-first benchmark orchestration

### `tests/evals/`

Owns during migration:

- legacy regression checks only

Must not own going forward:

- the primary benchmark runner path

## Test Strategy

New benchmark tests will live in `tests/benchmarking/` and cover:

- result schema
- contracts and profiles
- task registry
- runner orchestration
- LangSmith backend
- adapters
- criteria and evaluators
- trace sinks
- benchmark CLI

Existing runtime-related tests will be extended:

- `tests/test_runtime_wiring.py`
- `tests/test_task_10_run_service.py`
- targeted integration tests added under `tests/` as needed

`tests/conftest.py` will be updated so benchmark/eval gating no longer assumes `deepeval` is installed.

## Migration Policy

- `benchmarking/` is the only new benchmark feature path.
- `tracing/` is the only new benchmark-specific tracing feature path.
- `evaluation_service/custom_metrics/*` are sources for migrated criteria text only.
- `evaluation_service/deepeval_bridge.py` remains legacy until retirement conditions are met.
- `tests/evals/*` remain regression coverage only during overlap.
- DeepEval must not appear in the new benchmark-critical path.

## Implementation Order

1. Update dependencies and test gating.
2. Add `benchmarking/contracts.py`, `benchmarking/result_schema.py`, and `benchmarking/profiles.py`.
3. Add `tracing/config.py` and inject tracing config into `app/runtime.py`.
4. Replace benchmark-critical mock fallback behavior with explicit real-provider wiring.
5. Add recorder hooks and benchmark payload support in `core/loop/run_service.py`.
6. Add `tracing/sinks.py` and demote JSONL trace usage to mirror mode.
7. Implement task registry, runner, reporting, LangSmith backend, and benchmark CLI.
8. Implement `MLE-bench` and `QuantEval` adapters.
9. Migrate criteria/judge/rule evaluators and re-scope `tests/evals/`.
10. Add migration ledger and run focused verification plus smoke benchmarks.

## Risks

- The current repository already contains runtime evaluation paths that may partially overlap with benchmark scoring concerns.
- `trace_store/service.py` is simple today, so promoting LangSmith to primary sink requires careful abstraction rather than ad hoc branching.
- Existing tests assume top-level `tests/` layout, so introducing `tests/benchmarking/` must align with that style.
- External evaluators (`MLE-bench`, `QuantEval`) must remain import-light and testable without corpora downloads.

## Success Criteria

- New benchmark functionality lives under `benchmarking/` and `tracing/`, not `evaluation_service/`.
- The runtime exposes structured benchmark results and trace metadata without breaking pause/resume/fork behavior.
- LangSmith is the primary benchmark orchestration and trace sink.
- DeepEval is removed from benchmark-critical code paths.
- Legacy eval tests remain available only as migration/regression coverage.
