#!/usr/bin/env bash

set -euo pipefail

echo "[Task-17] Running acceptance matrix..."
python3 -m unittest \
  tests.test_task_14_cli_integration \
  tests.test_task_10_run_service \
  tests.test_task_08_execution_backend \
  tests.test_task_02_plugin_contracts \
  tests.test_task_17_reliability \
  tests.test_task_17_reproducibility

echo "[Task-17] Acceptance matrix passed."
