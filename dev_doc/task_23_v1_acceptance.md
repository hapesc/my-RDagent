# Task-23 V1 Acceptance and Hardening

## Acceptance matrix

- `A3 Branch`
  - `tests.test_task_14_cli_integration`
  - `tests.test_task_22_branch_aware_ui`
- `A5 Plugin Swap`
  - `tests.test_task_19_synthetic_research`
- API contract tests
  - `tests.test_task_18_v1_contracts`
  - `tests.test_task_21_control_plane`
  - `tests.test_task_23_v1_hardening`
- UI branch-aware tests
  - `tests.test_task_15_trace_ui`
  - `tests.test_task_22_branch_aware_ui`
- per-step override audit tests
  - `tests.test_task_20_per_step_config`
- security regressions
  - `tests.test_task_08_execution_backend`
  - `tests.test_task_16_observability_security`

## Smoke baselines

`tests.test_task_23_v1_hardening` validates two local smoke thresholds:

- metadata read path (`get_run + list_branches`) under `2s`
- UI first-screen helper load under `5s`

These are smoke checks on local SQLite/workspace scale, not throughput benchmarks.

## Acceptance command

```bash
./scripts/run_task23_acceptance.sh
```

The script runs full `test_task_*` discovery so acceptance output cannot silently skip newly added V1 regression modules.
