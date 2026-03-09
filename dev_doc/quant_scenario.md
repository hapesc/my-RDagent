# Quant Scenario: Alpha Factor Mining

## Overview

The `quant` scenario implements an automated alpha factor mining loop. An LLM proposes quantitative factors, a lightweight backtester evaluates them against real market data, and feedback drives the next iteration.

**Loop flow**: Propose factor hypothesis → Generate factor code → Backtest on OHLCV data → Analyze results → Repeat

## Architecture

```
                    ┌──────────────────────────────────────────┐
                    │            Loop Engine (generic)          │
                    │                                          │
                    │   propose → code → run → feedback → ...  │
                    └────────┬─────┬──────┬──────┬─────────────┘
                             │     │      │      │
                    ┌────────▼─────▼──────▼──────▼─────────────┐
                    │           Quant Plugin Bundle             │
                    │                                          │
                    │  QuantProposalEngine   (LLM)             │
                    │  QuantCoder            (LLM → factor.py) │
                    │  QuantRunner           (backtest)         │
                    │  QuantFeedbackAnalyzer (LLM)             │
                    └────────────────┬─────────────────────────┘
                                     │
                    ┌────────────────▼─────────────────────────┐
                    │          Data Provider (Protocol)         │
                    │                                          │
                    │  YFinanceDataProvider  (production)       │
                    │  MockDataProvider      (test-only)        │
                    └──────────────────────────────────────────┘
```

## Components

### QuantProposalEngine

Uses an LLM to propose factor hypotheses based on:
- The task summary (e.g., "mine alpha factors for QQQ, VOO, GOOG...")
- Previous iteration results (if any)
- Feedback from the last backtest

Output: a `Proposal` with summary, constraints, and virtual score.

### QuantCoder

Generates Python factor code via LLM. The generated function must follow this signature:

```python
def compute_factor(df: pd.DataFrame) -> pd.Series:
    """
    Args:
        df: OHLCV DataFrame with columns [date, stock_id, open, high, low, close, volume]
    Returns:
        pd.Series of factor values, same length as df
    """
```

Uses `generate_code()` (not `generate_structured()`) to extract both JSON metadata and a Python code block from the LLM response.

### QuantRunner

1. Loads OHLCV data from the configured `QuantDataProvider`
2. Executes the generated `factor.py` in a sandboxed `exec()` environment
3. Runs `LightweightBacktester` to compute backtest metrics

### LightweightBacktester

A pure-Python backtester (no external dependencies beyond pandas/numpy):
- Computes IC (information coefficient), ICIR, Sharpe ratio, max drawdown
- Uses simple long-short portfolio construction based on factor quintiles
- Validates factor output shape and NaN ratios

### QuantFeedbackAnalyzer

Summarizes backtest results via LLM, producing:
- `decision`: whether to accept the factor
- `reason`: explanation of strengths/weaknesses
- `observations`: raw metric summary
- Usefulness gate: Sharpe > 0.3, IC > 0.01 (configurable in `constants.py`)

## Data Providers

The `QuantDataProvider` protocol defines one method:

```python
class QuantDataProvider(Protocol):
    def load(self) -> pd.DataFrame:
        """Return OHLCV DataFrame: [date, stock_id, open, high, low, close, volume]"""
        ...
```

### YFinanceDataProvider (production)

Fetches real OHLCV data from Yahoo Finance via `yfinance`. Required for production use.

```python
from scenarios.quant.data_provider import YFinanceDataProvider

provider = YFinanceDataProvider(
    tickers=["QQQ", "VOO", "GOOG", "GLD", "SLV", "SCHD"],
    start="2022-01-01",
    end="2024-12-31",
)
df = provider.load()  # ~4500 rows
```

### MockDataProvider (test-only)

Generates synthetic GBM (Geometric Brownian Motion) data. **Only for unit/integration tests** — never used at runtime.

```python
from scenarios.quant.data_provider import MockDataProvider

provider = MockDataProvider(n_stocks=10, n_days=100, seed=42)
df = provider.load()
```

## Configuration

```python
@dataclass
class QuantConfig:
    workspace_root: str = "/tmp/rd_agent_workspace/quant"
    n_stocks: int = 50
    n_days: int = 500
    data_seed: int = 42
    backtest_config: Dict[str, Any] = field(default_factory=dict)
    default_step_overrides: StepOverrideConfig = ...
    data_provider: Optional[QuantDataProvider] = None  # REQUIRED at runtime
```

**`data_provider` must be set** — `QuantRunner.run()` raises `RuntimeError` if it's `None`.

## Usage

### Standalone E2E Test

```bash
export GEMINI_API_KEY=<your_key>
python scripts/run_quant_e2e.py
```

This script:
1. Builds an LLM adapter (Gemini 2.5 Pro via LiteLLM)
2. Fetches real OHLCV data via yfinance for QQQ, VOO, GOOG, GLD, SLV, SCHD
3. Wires the full runtime (loop engine, step executor, stores, etc.)
4. Runs one complete loop iteration
5. Prints backtest metrics and generated factor code

### Programmatic Usage

```python
from scenarios.quant.plugin import QuantConfig, build_quant_bundle
from scenarios.quant.data_provider import YFinanceDataProvider
from llm import LLMAdapter, LLMAdapterConfig
from llm.providers.litellm_provider import LiteLLMProvider

# Build LLM
provider = LiteLLMProvider(api_key="...", model="gemini/gemini-2.5-pro")
llm = LLMAdapter(provider=provider, config=LLMAdapterConfig(max_retries=2))

# Build quant bundle
config = QuantConfig(
    data_provider=YFinanceDataProvider(
        tickers=["QQQ", "VOO", "GOOG"],
        start="2023-01-01",
        end="2024-12-31",
    ),
)
bundle = build_quant_bundle(config=config, llm_adapter=llm)
# Register with PluginRegistry and use with loop engine...
```

## Code Safety

Factor code runs in a sandboxed `exec()` with restricted builtins. The `code_safety` module:
- Blocks dangerous builtins (`eval`, `exec`, `__import__`, `open`, etc.)
- Only allows `pandas`, `numpy`, and `math` imports
- Validates the presence of `compute_factor` function after execution

## File Structure

```
scenarios/quant/
├── __init__.py          # Public exports
├── plugin.py            # Plugin bundle, all scenario components
├── backtest.py          # LightweightBacktester
├── data_provider.py     # QuantDataProvider protocol + implementations
├── mock_data.py         # Synthetic GBM data generator (test-only)
├── metrics.py           # Metric computation helpers
├── prompts.py           # All LLM prompt templates
├── constants.py         # Metric thresholds and defaults
└── code_safety.py       # Sandboxed execution environment
```

## Design Decisions

- **No runtime mock** — `build_quant_bundle()` requires a real `LLMAdapter`; `QuantRunner` requires a real `QuantDataProvider`. Missing either raises `RuntimeError` with actionable error messages. See [ADR 007](architecture_decision_records/007-remove-runtime-mock.md).
- **Protocol-based data provider** — Any class implementing `load() -> pd.DataFrame` works, enabling easy swaps between yfinance, database, or custom providers.
- **Lightweight backtester** — Zero external dependencies beyond pandas/numpy. Computes IC, ICIR, Sharpe, max drawdown. Sufficient for fast iteration; not a production-grade backtesting engine.
