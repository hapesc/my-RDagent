#!/usr/bin/env bash

set -euo pipefail

echo "[Task-17] Running acceptance matrix..."
python3 -m unittest discover -s tests -p 'test_task_*.py'

echo "[Task-17] Acceptance matrix passed."
