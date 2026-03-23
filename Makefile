# Common developer commands for install, lint, test, verification, and releases.

.PHONY: test test-quick lint lint-fix format verify install install-all

test:
	uv run python -m pytest tests/ -q

test-quick:
	uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q

lint:
	uv run ruff check v3/ tests/ scripts/

lint-fix:
	uv run ruff check --fix v3/ tests/ scripts/

format:
	uv run ruff format v3/ tests/ scripts/

verify: lint test

install:
	bash scripts/setup_env.sh

install-all:
	bash scripts/setup_env.sh --all --scope-all --full-verify
