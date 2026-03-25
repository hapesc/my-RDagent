#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
One-click environment setup for my-RDagent-V3.

Usage:
  bash scripts/setup_env.sh [options]

Runtime selection:
  --claude        Install skills for Claude Code
  --codex         Install skills for Codex
  --all           Install skills for both Claude Code and Codex

Location selection:
  --local         Install into repo-local runtime roots (default)
  --global        Install into home-directory runtime roots
  --scope-all     Install into both local and global runtime roots

Install mode:
  --link          Symlink skills into the target root (default)
  --copy          Copy skills into the target root

Verification:
  --quick-verify  Run the quick verification suite (default)
  --full-verify   Run the full verification suite
  --skip-verify   Skip pytest/import-linter verification

Other:
  -h, --help      Show this help text

Defaults:
  --claude --local --link --quick-verify

Examples:
  bash scripts/setup_env.sh
  bash scripts/setup_env.sh --claude --global
  bash scripts/setup_env.sh --all --scope-all --full-verify
EOF
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "error: required command not found: $command_name" >&2
    exit 1
  fi
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

runtime="claude"
scope="local"
mode="link"
verification="quick"

while (($# > 0)); do
  case "$1" in
    --claude)
      runtime="claude"
      ;;
    --codex)
      runtime="codex"
      ;;
    --all)
      runtime="all"
      ;;
    --local)
      scope="local"
      ;;
    --global)
      scope="global"
      ;;
    --scope-all)
      scope="all"
      ;;
    --link)
      mode="link"
      ;;
    --copy)
      mode="copy"
      ;;
    --quick-verify)
      verification="quick"
      ;;
    --full-verify)
      verification="full"
      ;;
    --skip-verify)
      verification="skip"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      echo >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

require_command uv

cd "$REPO_ROOT"

echo "==> Syncing repo environment with uv"
uv sync --extra test

echo "==> Installing repo-local skills"
uv run python scripts/install_agent_skills.py \
  --runtime "$runtime" \
  --scope "$scope" \
  --mode "$mode"

echo "==> Checking CLI surface"
uv run rdagent-tool list >/dev/null

case "$verification" in
  quick)
    echo "==> Running quick verification"
    uv run python -m pytest \
      tests/test_v3_tool_cli.py \
      tests/test_phase17_surface_convergence.py \
      tests/test_phase18_skill_installation.py \
      tests/test_phase18_planning_continuity.py \
      -q
    ;;
  full)
    echo "==> Running full verification"
    uv run python -m pytest \
      tests/test_v3_tool_cli.py \
      tests/test_phase13_v3_tools.py \
      tests/test_phase14_skill_agent.py \
      tests/test_phase16_rd_agent.py \
      tests/test_phase16_tool_surface.py \
      tests/test_phase17_surface_convergence.py \
      tests/test_phase18_skill_installation.py \
      tests/test_phase18_planning_continuity.py \
      -q
    uv run lint-imports
    ;;
  skip)
    echo "==> Skipping verification"
    ;;
esac

echo
echo "Setup complete."
echo
echo "Recommended next steps:"
if [[ "$runtime" == "claude" || "$runtime" == "all" ]]; then
  echo "  Claude Code: /rd-agent"
fi
if [[ "$runtime" == "codex" || "$runtime" == "all" ]]; then
  echo "  Codex: \$rd-agent"
fi
echo "  CLI catalog: uv run rdagent-tool list"
