# Common developer commands for install, lint, test, verification, and releases.

.PHONY: test test-quick lint lint-fix format verify install install-all release

test:
	uv run python -m pytest tests/ -q

test-quick:
	uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase17_surface_convergence.py tests/test_phase18_skill_installation.py tests/test_phase18_planning_continuity.py -q

lint:
	uv run ruff check rd_agent/ tests/ scripts/

lint-fix:
	uv run ruff check --fix rd_agent/ tests/ scripts/

format:
	uv run ruff format rd_agent/ tests/ scripts/

verify: lint test

install:
	bash scripts/setup_env.sh

install-all:
	bash scripts/setup_env.sh --all --scope-all --full-verify

release:
	@if [ -z "$(VERSION)" ]; then \
		echo "error: VERSION is required (example: make release VERSION=1.3.0)"; \
		exit 1; \
	fi
	uv run python scripts/bump_version.py $(VERSION)
