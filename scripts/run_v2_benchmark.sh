#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/run_v2_benchmark.sh [options]

Run the real v2 smoke benchmark for one or more scenarios.

Options:
  --profile <name>         Benchmark profile to run. Default: smoke
  --output-root <path>     Root output directory. Default: /tmp/v2-benchmark-<profile>
  --scenario <name>        Scenario to run. Repeatable. Default: data_science, quant
  --compare-baseline <p>   Optional baseline JSON path passed through to the Python CLI
  --upload-results         Upload results through the Python CLI
  --help                   Show this help text

Required environment for real benchmark:
  RD_AGENT_LLM_PROVIDER    Must be set and must not be "mock"
  RD_AGENT_LLM_MODEL       Must be set
  RD_AGENT_LLM_API_KEY     Required unless your provider path supports auth without it
EOF
}

PROFILE="smoke"
OUTPUT_ROOT=""
COMPARE_BASELINE=""
UPLOAD_RESULTS="false"
SCENARIOS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:?missing value for --profile}"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="${2:?missing value for --output-root}"
      shift 2
      ;;
    --scenario)
      SCENARIOS+=("${2:?missing value for --scenario}")
      shift 2
      ;;
    --compare-baseline)
      COMPARE_BASELINE="${2:?missing value for --compare-baseline}"
      shift 2
      ;;
    --upload-results)
      UPLOAD_RESULTS="true"
      shift
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${RD_AGENT_LLM_PROVIDER:-}" ]]; then
  echo "RD_AGENT_LLM_PROVIDER must be set for a real provider benchmark." >&2
  exit 1
fi

if [[ "${RD_AGENT_LLM_PROVIDER}" == "mock" ]]; then
  echo "This script only runs real provider benchmarks; RD_AGENT_LLM_PROVIDER=mock is not allowed." >&2
  exit 1
fi

if [[ -z "${RD_AGENT_LLM_MODEL:-}" ]]; then
  echo "RD_AGENT_LLM_MODEL must be set for a real provider benchmark." >&2
  exit 1
fi

if [[ ${#SCENARIOS[@]} -eq 0 ]]; then
  SCENARIOS=("data_science" "quant")
fi

if [[ -z "${OUTPUT_ROOT}" ]]; then
  OUTPUT_ROOT="/tmp/v2-benchmark-${PROFILE}"
fi

mkdir -p "${OUTPUT_ROOT}"

for scenario in "${SCENARIOS[@]}"; do
  scenario_output="${OUTPUT_ROOT}/${scenario}"
  mkdir -p "${scenario_output}"

  cmd=(
    uv run python scripts/run_langsmith_benchmark.py
    --profile "${PROFILE}"
    --scenario "${scenario}"
    --output-dir "${scenario_output}"
  )

  if [[ -n "${COMPARE_BASELINE}" ]]; then
    cmd+=(--compare-baseline "${COMPARE_BASELINE}")
  fi

  if [[ "${UPLOAD_RESULTS}" == "true" ]]; then
    cmd+=(--upload-results)
  fi

  echo "Running ${scenario} benchmark -> ${scenario_output}"
  UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" "${cmd[@]}"
done

echo "Benchmark outputs:"
find "${OUTPUT_ROOT}" -maxdepth 2 -type f | sort
