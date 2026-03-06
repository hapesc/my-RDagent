#!/usr/bin/env bash
set -euo pipefail

python3 -m unittest discover -s tests -p 'test_task_*.py'

echo "Task-23 V1 acceptance passed"
