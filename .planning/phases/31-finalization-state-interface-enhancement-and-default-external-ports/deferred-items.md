# Deferred Items

- 2026-03-25: `uv run pytest -x -q` still fails in `tests/test_phase20_stage_skill_contracts.py` because `skills/*/workflows/continue.md` no longer contains the legacy `## Required fields` continuation skeleton text. This predates Phase 31 scope and is unrelated to finalization-state work, so it was not modified here.
