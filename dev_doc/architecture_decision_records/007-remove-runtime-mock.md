# ADR 007: Remove Runtime Mock Fallback

## Status
Accepted

## Context

The platform originally provided `MockLLMProvider` as a fallback when no real LLM backend was configured. Each scenario's `build_*_bundle()` function would silently instantiate a mock provider if `llm_adapter=None` was passed. Similarly, the quant scenario could fall back to synthetic data when no real data provider was configured.

This caused several problems:

1. **Silent failures**: Users would run the platform thinking they had a working setup, only to get nonsensical mock outputs. The mock responses masked configuration errors.
2. **False confidence**: Integration tests using mocks passed, but the real pipeline had prompt/parsing issues that only surfaced with actual LLM calls (e.g., Gemini returning empty responses, CodeDraft parsing failures).
3. **Debugging difficulty**: When something went wrong, it was unclear whether the issue was in the code, the prompt, or the mock data.
4. **Architectural confusion**: The boundary between "test mock" and "production fallback" was blurred.

## Decision

**Remove all runtime mock fallbacks. Keep mocks only for unit/integration tests.**

Specifically:
- `build_data_science_bundle(llm_adapter=None)` → raises `RuntimeError` instead of falling back to `MockLLMProvider`
- `build_synthetic_research_bundle(llm_adapter=None)` → raises `RuntimeError`
- `build_quant_bundle(llm_adapter=None)` → raises `RuntimeError`
- `QuantRunner.run()` with `data_provider=None` → raises `RuntimeError`
- `build_runtime()` in `app/runtime.py` → raises `RuntimeError` if LLM provider is not configured

All error messages are actionable — they tell the user exactly what to configure and how.

## Test-Only Mocks

Mocks remain available for tests:
- `MockLLMProvider` in `llm/providers/mock.py` — used by unit tests via `conftest.py` fixtures
- `MockDataProvider` in `scenarios/quant/mock_data.py` — generates synthetic GBM data for quant unit tests

These are never imported or used in production code paths.

## Consequences

- **Fail-fast**: Misconfigured deployments fail immediately with a clear error, not silently with garbage output.
- **Real validation**: The only way to run the platform is with real backends, ensuring prompt/parsing issues are caught early.
- **Cleaner separation**: Test code and production code have distinct dependency paths.
- **Slight increase in setup friction**: Users must configure an LLM API key before their first run. The error messages guide them through this.
