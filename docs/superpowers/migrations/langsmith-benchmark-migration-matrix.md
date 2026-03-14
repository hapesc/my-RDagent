# LangSmith Benchmark Migration Matrix

## Scope

- `benchmarking/` is the only new benchmark feature path.
- `tracing/` is the only new benchmark-specific tracing feature path.
- `evaluation_service/` legacy evaluator assets are migration sources, not new feature targets.
- `tests/evals/` is legacy regression coverage during the overlap period, not the primary benchmark runner.

## Dual-Run Policy

- Old and new benchmark paths may run in parallel during the migration overlap period.
- No new benchmark feature work lands in `evaluation_service/`.
- New benchmark orchestration, reporting, adapters, and evaluators land only in `benchmarking/` and `tracing/`.
- Legacy `tests/evals/` remain gated behind `--run-evals` until retirement conditions are met.

## Asset Matrix

| Source Asset | Target / Replacement | Status | Retirement Condition |
|---|---|---:|---|
| `evaluation_service/deepeval_bridge.py` | `benchmarking/evaluators/judge.py` input dictionaries + direct evaluator calls | legacy-only | Drop when `tests/evals/*` no longer needs `LLMTestCase` conversion and no benchmark path imports the bridge |
| `evaluation_service/custom_metrics/proposal_quality.py` | `benchmarking/evaluators/criteria.py` + `benchmarking/evaluators/judge.py` | migrated | Retire when proposal regressions run only through new judge evaluators |
| `evaluation_service/custom_metrics/costeer_efficiency.py` | `benchmarking/evaluators/criteria.py` + `benchmarking/evaluators/judge.py`; pure Python efficiency helpers may remain legacy-only | replaced | Retire or narrow to pure utility usage once no benchmark test imports DeepEval metrics |
| `evaluation_service/custom_metrics/report_quality.py` | `benchmarking/evaluators/criteria.py` + `benchmarking/evaluators/judge.py` | migrated | Retire when report regressions no longer reference legacy metrics |
| `evaluation_service/custom_metrics/code_quality.py` | `benchmarking/evaluators/rules.py` and future codegen-specific judge coverage | legacy-only | Drop once codegen regression coverage is fully expressed through new benchmark rule/judge layers |
| `tests/evals/test_p0_codegen.py` | Structural regression around `benchmarking.evaluators.rules` | replaced | Retire or move when codegen legacy regression is either folded into `tests/benchmarking/` or superseded by dedicated benchmark runner coverage |
| `tests/evals/test_p1_costeer.py` | Regression around `benchmarking.evaluators.judge` feedback actionability + pure Python efficiency helpers | migrated | Retire when costeer regression coverage is consolidated into new benchmark evaluator tests |
| `tests/evals/test_p2_proposal.py` | Regression around `benchmarking.evaluators.judge` proposal judges | migrated | Retire when proposal regression coverage moves fully under `tests/benchmarking/` |
| `tests/evals/test_p3_report.py` | Regression around `benchmarking.evaluators.judge` report judges | migrated | Retire when report regression coverage moves fully under `tests/benchmarking/` |
| `tests/evals/test_p4_dataset_expansion.py` | Legacy dataset regression, optionally move to `tests/benchmarking/test_task_registry.py` | legacy-only | Move or drop when dataset integrity checks are covered under `tests/benchmarking/` |
| `tests/evals/conftest.py` | Legacy real-LLM regression fixtures | legacy-only | Remove when `tests/evals/` no longer needs LLM-backed regression runs |
| `tests/conftest.py` `--run-evals` gate | Legacy regression gate for `tests/evals/` | replaced | Simplify or remove when `tests/evals/` is retired |
| `pyproject.toml` `deepeval` dependency | None in benchmark-critical path | drop | Remove when no runtime path and no retained legacy regression requires `deepeval` |

## Path Rules

- `benchmarking/` is the authoritative path for:
  - result schemas
  - contracts
  - profiles
  - task registry
  - runner
  - reporting
  - LangSmith backend
  - adapters
  - criteria/judge/rule evaluators
- `tracing/` is the authoritative path for:
  - tracing config
  - recorder protocol
  - sink fanout
- `evaluation_service/` remains legacy-only during overlap.

## Verification Notes

- New benchmark-critical paths must have zero runtime dependency on `deepeval`.
- Legacy references that remain in `evaluation_service/` or `tests/evals/` are intentionally `legacy-only` until retirement conditions are met.
- The migration is complete only when the `deepeval` dependency can be dropped from `pyproject.toml` without breaking benchmark or regression commitments.
