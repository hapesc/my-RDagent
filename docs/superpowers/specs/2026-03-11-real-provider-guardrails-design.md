# Real Provider Guardrails Design

## Goal

Stop blocking startup and runtime assembly when a real-provider configuration exceeds the conservative profile. Keep warnings so operators are told that execution may take a long time.

## Decision

- Remove all real-provider hard limits from `app/config.py`.
- Keep only semantic validation that rejects invalid configurations, specifically `layer0_k_forward > layer0_n_candidates`.
- Preserve conservative-profile warnings, but change the message to explicitly say that execution may take a long time.
- Apply the same non-blocking behavior to per-step retry and timeout overrides.

## Scope

- `app/config.py`
- `tests/test_runtime_wiring.py`
- `tests/test_integration_full_loop.py`

## Non-Goals

- No changes to runtime defaults.
- No changes to planner behavior or safe-profile metadata.
- No changes to CLI error formatting except where the old error path disappears.
