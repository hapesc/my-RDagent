# Quant Scenario Plugin

## TL;DR

> **Quick Summary**: 为 my-RDagent 实现量化交易（quant）场景插件，包含 factor mining 循环（LLM 生成 alpha factor → 轻量回测 → 指标评估 → 反馈改进）和完整的 PluginBundle 实现。
> 
> **Deliverables**:
> - `scenarios/quant/` 完整插件模块（plugin.py, backtest.py, metrics.py, mock_data.py, prompts.py）
> - 轻量级内置回测引擎（纯 Python，不依赖 Qlib/backtrader）
> - 标准量化指标计算（IC, ICIR, Sharpe, MDD, ARR, Calmar）
> - 插件注册到 PluginRegistry
> - 完整 TDD 测试套件
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 1 (mock data) → Task 4 (metrics) → Task 6 (backtest) → Task 8 (runner) → Task 10 (plugin bundle) → Task 12 (integration) → Final Verification

---

## Context

### Original Request
用户要求为项目补完论文中的 quant 场景。用户明确指定：(1) quant 优先于 finance；(2) 需要内置轻量级回测环境；(3) 量化指标由我们根据研究确定。

### Interview Summary
**Key Discussions**:
- **优先级**: Quant 第一，Finance 以后再说
- **回测方案**: 内置轻量级 Python 回测，不依赖 Qlib/backtrader 等外部框架
- **指标选择**: IC, ICIR, Rank IC, Rank ICIR, Sharpe, MDD, ARR, Calmar（基于论文 + web research）
- **测试策略**: TDD（用户明确选择）
- **简化策略**: 单一 factor mining 循环（暂不做 dual factor+model multi-armed bandit）

**Research Findings**:
- **原版 RDAgent**: 使用 Qlib + CSI300 + TopkDropoutStrategy + Factor/Model CoSTEER
- **NeurIPS 2025 论文**: 5-unit 架构，multi-armed bandit 调度 factor/model，IC correlation 去重
- **接口映射**: 完整 PluginBundle 接口已文档化（explore agent），所有方法签名、数据类型、wiring 点

### Gap Analysis (替代 Metis)
**Identified Gaps** (addressed below):
1. **Mock 数据现实性** → 增加市场相关性结构、OHLC 约束验证
2. **Forward-looking bias** → 增加时间分割 train/valid/test，禁止未来数据
3. **反馈主指标歧义** → 定义 Sharpe 为主指标，其他为约束
4. **代码执行可靠性** → 增加 AST 检查 + import 白名单 + 错误处理
5. **因子退化** → 增加 all-NaN 检测、常量因子过滤、重复检测
6. **验收标准缺失** → 每个 task 增加明确的 AC

---

## Work Objectives

### Core Objective
实现一个完整的 quant scenario 插件，使 RDAgent 能自动进行 alpha factor mining：LLM 提出因子假设 → 生成因子代码 → 回测评估 → 反馈改进，循环迭代直到发现有效因子。

### Concrete Deliverables
- `scenarios/quant/__init__.py` — 模块入口 + `build_quant_bundle()` 导出
- `scenarios/quant/plugin.py` — 6 个插件组件实现
- `scenarios/quant/backtest.py` — 轻量级回测引擎
- `scenarios/quant/metrics.py` — 量化指标计算库
- `scenarios/quant/mock_data.py` — 合成市场数据生成器
- `scenarios/quant/prompts.py` — Quant 专用 LLM prompt 模板
- `scenarios/quant/constants.py` — 阈值、配置常量
- `plugins/__init__.py` 修改 — 注册 quant 插件
- `tests/test_quant_*.py` — 完整 TDD 测试套件（≥20 tests）

### Definition of Done
- [ ] `python3 -m pytest tests/test_quant_* -q` → ALL PASS
- [ ] `python3 -m pytest tests/ -q` → 所有已有 638+ tests 仍 PASS（无回归）
- [ ] `python3 -c "from scenarios.quant import build_quant_bundle; b = build_quant_bundle(); print(b.scenario_name)"` → 输出 "quant"
- [ ] 完整 factor mining 循环可执行（propose → code → run → feedback）

### Must Have
- 遵循现有 PluginBundle 架构，与 data_science/synthetic_research 保持一致
- artifacts_ref 格式为 `json.dumps(list_of_paths)`
- step_config 正确传播
- scene_usefulness_validator 实现 quant-specific 验证
- Train/Test 时间分割（防止 forward-looking bias）
- 主指标为 Sharpe，其他指标为约束条件
- Mock 数据满足 OHLC 约束（High ≥ Open/Close ≥ Low）
- 生成代码的 AST 安全检查（禁止 os/subprocess/requests）
- All-NaN / 常量因子自动拒绝

### Must NOT Have (Guardrails)
- ❌ 不依赖 Qlib、backtrader、vectorbt 等外部回测框架
- ❌ 不实现多因子融合/组合优化（v1 仅单因子）
- ❌ 不实现 dual factor+model multi-armed bandit 调度
- ❌ 不接入真实市场数据 API（纯 mock 数据）
- ❌ 不实现实盘交易/live trading 接口
- ❌ 不实现订单簿/L2 微观结构
- ❌ 不实现风险模型/敞口约束
- ❌ 不修改核心框架代码（core/、app/ 等），仅在 scenarios/ 和 plugins/ 中工作
- ❌ 不添加超过 stdlib + numpy + pandas 的依赖
- ❌ 不过度注释、不添加 JSDoc-style docstring bloat、不过度抽象

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest, 638 tests)
- **Automated tests**: TDD (RED-GREEN-REFACTOR)
- **Framework**: pytest
- **If TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Library/Module**: Use Bash (python3 REPL / pytest) — Import, call functions, compare output
- **Plugin Integration**: Use Bash (pytest + python3 -c) — Run full chain, verify output format

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation + data layer):
├── Task 1: Mock data generator + tests [quick] — TDD
├── Task 2: Constants & config module [quick] — TDD
└── Task 3: Quant prompt templates [quick]

Wave 2 (After Wave 1 — metrics + backtest):
├── Task 4: Metrics computation library + tests [deep] — TDD
├── Task 5: Code safety validator + tests [quick] — TDD
└── Task 6: Backtest engine + tests [deep] — TDD

Wave 3 (After Wave 2 — plugin components):
├── Task 7: ScenarioPlugin + ProposalEngine [unspecified-high] — TDD
├── Task 8: ExperimentGenerator + Coder [unspecified-high] — TDD
├── Task 9: Runner (wraps backtest engine) [unspecified-high] — TDD
├── Task 10: FeedbackAnalyzer + UsefulnessGateValidator [unspecified-high] — TDD
└── Task 11: PluginBundle assembly + registry [quick] — TDD

Wave 4 (After Wave 3 — integration + verification):
├── Task 12: Full-chain integration test [deep] — TDD
└── Task 13: Regression test (ensure 638 existing tests pass) [quick]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real QA — run full factor mining loop (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: T1 → T4 → T6 → T9 → T11 → T12 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 3 (Waves 1, 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 4, 5, 6, 7, 8, 9, 10 | 1 |
| 2 | — | 4, 5, 6, 7, 8, 9, 10 | 1 |
| 3 | — | 7, 8 | 1 |
| 4 | 1, 2 | 6, 9, 10 | 2 |
| 5 | 2 | 8, 9 | 2 |
| 6 | 1, 2, 4 | 9 | 2 |
| 7 | 1, 2, 3 | 11 | 3 |
| 8 | 1, 2, 3, 5 | 11 | 3 |
| 9 | 1, 2, 4, 5, 6 | 11 | 3 |
| 10 | 1, 2, 4 | 11 | 3 |
| 11 | 7, 8, 9, 10 | 12 | 3 |
| 12 | 11 | F1-F4 | 4 |
| 13 | 11 | F1-F4 | 4 |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 `quick`, T2 `quick`, T3 `quick`
- **Wave 2**: 3 tasks — T4 `deep`, T5 `quick`, T6 `deep`
- **Wave 3**: 5 tasks — T7 `unspecified-high`, T8 `unspecified-high`, T9 `unspecified-high`, T10 `unspecified-high`, T11 `quick`
- **Wave 4**: 2 tasks — T12 `deep`, T13 `quick`
- **FINAL**: 4 tasks — F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

### Wave 1 — Foundation & Data Layer (Start Immediately, 3 parallel)

- [ ] 1. Mock Data Generator + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_mock_data.py` with tests:
    - `test_generate_ohlcv_shape` — 50 stocks × 500 days, columns: date, stock_id, open, high, low, close, volume
    - `test_ohlcv_constraints` — High ≥ max(Open, Close), Low ≤ min(Open, Close), Volume > 0
    - `test_market_correlation_structure` — stocks have pairwise correlation > 0 (not pure random)
    - `test_no_missing_dates` — no gaps in trading days (weekdays only)
    - `test_returns_distribution` — daily returns roughly normal, mean ≈ 0, std ≈ 0.01-0.03
    - `test_generate_with_custom_params` — configurable n_stocks, n_days, start_date
    - `test_reproducibility` — same seed → same data
  - GREEN: Implement `scenarios/quant/mock_data.py`:
    - `generate_ohlcv(n_stocks=50, n_days=500, start_date="2020-01-01", seed=42) -> pd.DataFrame`
    - Use correlated GBM (Geometric Brownian Motion) for realistic price paths
    - Columns: `["date", "stock_id", "open", "high", "low", "close", "volume"]`
    - Stock IDs: `["STOCK_001", ..., "STOCK_050"]`
    - Include realistic overnight gaps (open ≠ previous close)
    - Volume as lognormal distribution
  - REFACTOR: Extract constants (default params) to constants.py

  **Must NOT do**:
  - ❌ Do NOT use real market data or API calls
  - ❌ Do NOT add yfinance/pandas-datareader dependencies
  - ❌ Do NOT model intraday data (daily OHLCV only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file + test file, straightforward numpy/pandas work
  - **Skills**: []
    - No special skills needed — standard Python with numpy/pandas

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 4, 5, 6, 7, 8, 9, 10
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL):

  **Pattern References**:
  - `scenarios/data_science/plugin.py:350-380` — How data_science Runner generates synthetic data inline; follow similar approach for mock_data.py as a standalone module
  - `scenarios/synthetic_research/plugin.py:480-510` — How synthetic_research generates mock research data

  **API/Type References**:
  - `data_models.py` — No direct dependency, but mock_data output (pd.DataFrame) will be consumed by backtest.py (Task 6) and metrics.py (Task 4)

  **External References**:
  - Geometric Brownian Motion: `dS = μ·S·dt + σ·S·dW` — standard model for synthetic stock prices
  - Cholesky decomposition for correlated random walks: `L = cholesky(correlation_matrix); correlated_shocks = L @ independent_shocks`

  **WHY Each Reference Matters**:
  - data_science plugin shows how existing scenarios handle synthetic data — follow the "generate inside module, no external deps" pattern
  - GBM + Cholesky ensures mock data has realistic statistical properties (not pure random noise), so factor mining actually has meaningful signals to discover

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_mock_data.py`
  - [ ] `python3 -m pytest tests/test_quant_mock_data.py -q` → PASS (≥7 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Happy path — generate default OHLCV data
    Tool: Bash (python3 -c)
    Preconditions: scenarios/quant/mock_data.py exists
    Steps:
      1. python3 -c "from scenarios.quant.mock_data import generate_ohlcv; df = generate_ohlcv(); print(df.shape); print(df.columns.tolist()); print(df.dtypes)"
      2. Assert output contains: (25000, 7) — 50 stocks × 500 days
      3. Assert columns: ['date', 'stock_id', 'open', 'high', 'low', 'close', 'volume']
    Expected Result: Shape is (25000, 7), all columns present, no errors
    Failure Indicators: ImportError, shape mismatch, missing columns
    Evidence: .sisyphus/evidence/task-1-mock-data-happy.txt

  Scenario: OHLC constraint validation
    Tool: Bash (python3 -c)
    Preconditions: mock data generated
    Steps:
      1. python3 -c "from scenarios.quant.mock_data import generate_ohlcv; df = generate_ohlcv(); violations = df[df['high'] < df[['open','close']].max(axis=1)]; print(f'High violations: {len(violations)}'); violations2 = df[df['low'] > df[['open','close']].min(axis=1)]; print(f'Low violations: {len(violations2)}')"
      2. Assert: High violations: 0, Low violations: 0
    Expected Result: Zero OHLC constraint violations
    Failure Indicators: Any violation count > 0
    Evidence: .sisyphus/evidence/task-1-mock-data-ohlc.txt
  ```

  **Commit**: YES (groups with T2, T3)
  - Message: `feat(quant): add mock data, constants, and prompt templates`
  - Files: `scenarios/quant/mock_data.py`, `scenarios/quant/__init__.py`, `tests/test_quant_mock_data.py`
  - Pre-commit: `pytest tests/test_quant_mock_data.py -q`

- [ ] 2. Constants & Config Module + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_constants.py` with tests:
    - `test_metric_thresholds_exist` — all 8 metrics have defined thresholds
    - `test_threshold_ranges_valid` — Sharpe threshold > 0, IC threshold in (0, 1), MDD threshold in (-1, 0)
    - `test_default_backtest_config` — default rebalance frequency, train/test split dates, initial capital
    - `test_import_whitelist` — safe imports list exists and contains numpy, pandas
    - `test_import_blacklist` — dangerous imports blocked: os, subprocess, requests, shutil
  - GREEN: Implement `scenarios/quant/constants.py`:
    - `METRIC_THRESHOLDS`: dict mapping metric name → minimum acceptable value
      - `{"sharpe": 0.5, "ic": 0.02, "icir": 0.3, "rank_ic": 0.02, "rank_icir": 0.3, "arr": 0.03, "mdd": -0.35, "calmar": 1.0}`
    - `PRIMARY_METRIC = "sharpe"` — main optimization target
    - `CONSTRAINT_METRICS = ["ic", "icir", "mdd"]` — must-pass constraints
    - `BACKTEST_CONFIG`: dataclass or dict with:
      - `rebalance_freq = "daily"` (daily rebalance)
      - `train_end = "2021-06-30"`, `test_start = "2021-07-01"` (50/50 split of 500 days)
      - `initial_capital = 1_000_000`
      - `commission_rate = 0.001` (0.1% per trade)
      - `slippage_rate = 0.001` (0.1% slippage)
    - `SAFE_IMPORTS = {"numpy", "pandas", "math", "statistics", "functools", "itertools"}`
    - `BLOCKED_IMPORTS = {"os", "subprocess", "shutil", "requests", "urllib", "socket", "sys", "importlib"}`
    - `MAX_FACTOR_COMPUTE_SEC = 30` — timeout for factor computation
    - `MAX_FACTOR_MEMORY_MB = 512` — memory limit
  - REFACTOR: Ensure all downstream modules import from constants.py

  **Must NOT do**:
  - ❌ Do NOT hardcode thresholds in other modules — centralize here
  - ❌ Do NOT make thresholds too strict (this is for LLM-generated factors, not production)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single config file with simple dataclass/dict definitions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 4, 5, 6, 7, 8, 9, 10
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:1-30` — How data_science defines inline constants (we extract to separate module for cleanliness)
  - `service_contracts.py:StepOverrideConfig` — Pattern for config dataclass with defaults

  **API/Type References**:
  - `service_contracts.py:StepOverrideConfig` — This is the step_config type that must be propagated in build_context

  **WHY Each Reference Matters**:
  - data_science puts constants inline; we create a dedicated module because quant has many more config values
  - StepOverrideConfig shows the project's preferred pattern for config objects with defaults

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_constants.py`
  - [ ] `python3 -m pytest tests/test_quant_constants.py -q` → PASS (≥5 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Constants importable and complete
    Tool: Bash (python3 -c)
    Preconditions: scenarios/quant/constants.py exists
    Steps:
      1. python3 -c "from scenarios.quant.constants import METRIC_THRESHOLDS, PRIMARY_METRIC, SAFE_IMPORTS, BLOCKED_IMPORTS, BACKTEST_CONFIG; print(f'Thresholds: {len(METRIC_THRESHOLDS)} metrics'); print(f'Primary: {PRIMARY_METRIC}'); print(f'Safe imports: {len(SAFE_IMPORTS)}'); print(f'Blocked: {len(BLOCKED_IMPORTS)}')"
      2. Assert: Thresholds: 8 metrics, Primary: sharpe, Safe imports: ≥6, Blocked: ≥8
    Expected Result: All constants accessible with correct counts
    Failure Indicators: ImportError, wrong counts
    Evidence: .sisyphus/evidence/task-2-constants-happy.txt

  Scenario: Blocked imports do not overlap with safe imports
    Tool: Bash (python3 -c)
    Preconditions: constants module loaded
    Steps:
      1. python3 -c "from scenarios.quant.constants import SAFE_IMPORTS, BLOCKED_IMPORTS; overlap = SAFE_IMPORTS & BLOCKED_IMPORTS; print(f'Overlap: {overlap}'); assert len(overlap) == 0, f'Overlap found: {overlap}'"
      2. Assert: Overlap: set(), no assertion error
    Expected Result: Zero overlap between safe and blocked imports
    Failure Indicators: AssertionError with overlapping modules
    Evidence: .sisyphus/evidence/task-2-constants-overlap.txt
  ```

  **Commit**: YES (groups with T1, T3)
  - Message: `feat(quant): add mock data, constants, and prompt templates`
  - Files: `scenarios/quant/constants.py`, `tests/test_quant_constants.py`
  - Pre-commit: `pytest tests/test_quant_constants.py -q`

- [ ] 3. Quant Prompt Templates

  **What to do**:
  - Create `scenarios/quant/prompts.py` with quant-specific LLM prompt templates:
    - `FACTOR_PROPOSAL_SYSTEM_PROMPT` — System prompt for factor hypothesis generation
      - Explain: you are a quantitative researcher, propose alpha factors for stock prediction
      - Include: what makes a good factor (predictive of future returns, not forward-looking, diversified)
    - `FACTOR_PROPOSAL_USER_TEMPLATE` — User prompt template with placeholders:
      - `{task_summary}` — the research task
      - `{previous_factors}` — list of previously tried factors and their performance
      - `{feedback}` — feedback from last iteration
    - `FACTOR_CODE_SYSTEM_PROMPT` — System prompt for factor code generation
      - Explain: generate Python code that computes a single alpha factor from OHLCV data
      - Include: available columns (date, stock_id, open, high, low, close, volume)
      - Include: expected output format (DataFrame with columns: date, stock_id, factor_value)
      - Include: constraints (no future data, must use only pandas/numpy, handle NaN)
    - `FACTOR_CODE_USER_TEMPLATE` — User prompt with `{factor_hypothesis}`, `{data_schema}`
    - `FEEDBACK_ANALYSIS_TEMPLATE` — Template for analyzing backtest results
      - Include: metric definitions and thresholds
      - Include: what to improve based on results
    - `FACTOR_CODE_EXAMPLE` — A concrete example of a valid factor implementation:
      ```python
      def compute_factor(df: pd.DataFrame) -> pd.DataFrame:
          """5-day momentum factor."""
          result = df.copy()
          result['factor_value'] = df.groupby('stock_id')['close'].pct_change(5)
          return result[['date', 'stock_id', 'factor_value']]
      ```
  - No separate test file needed — prompts are string constants, tested via integration (Task 12)

  **Must NOT do**:
  - ❌ Do NOT put prompts in llm/prompts.py — keep in scenarios/quant/prompts.py for encapsulation
  - ❌ Do NOT include actual market knowledge (no "buy low sell high" tips) — keep domain-neutral
  - ❌ Do NOT make prompts too long (< 2000 chars each)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Writing prompt strings — no complex logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 7, 8
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `llm/prompts.py` — Existing prompt templates in the project; follow the same naming convention and f-string placeholder style
  - `scenarios/data_science/plugin.py:55-95` — How data_science ProposalEngine constructs its prompts from templates

  **External References**:
  - R&D-Agent-Quant paper (arxiv 2505.15155): Factor specification prompts should guide LLM to propose factors with: (1) name, (2) hypothesis, (3) formulation, (4) expected behavior
  - Original RDAgent docs: Factor code template expects `def compute_factor(df)` signature returning factor values

  **WHY Each Reference Matters**:
  - llm/prompts.py shows the project's existing prompt style — we should match it for consistency
  - The paper's factor specification structure (name, hypothesis, formulation) is proven to work well with LLMs

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All prompts importable and non-empty
    Tool: Bash (python3 -c)
    Preconditions: scenarios/quant/prompts.py exists
    Steps:
      1. python3 -c "from scenarios.quant.prompts import FACTOR_PROPOSAL_SYSTEM_PROMPT, FACTOR_CODE_SYSTEM_PROMPT, FACTOR_CODE_EXAMPLE, FEEDBACK_ANALYSIS_TEMPLATE; print(f'Proposal: {len(FACTOR_PROPOSAL_SYSTEM_PROMPT)} chars'); print(f'Code: {len(FACTOR_CODE_SYSTEM_PROMPT)} chars'); print(f'Example: {len(FACTOR_CODE_EXAMPLE)} chars'); print(f'Feedback: {len(FEEDBACK_ANALYSIS_TEMPLATE)} chars')"
      2. Assert: all lengths > 100 chars
    Expected Result: All 4+ prompt constants importable with meaningful content
    Failure Indicators: ImportError, length < 100
    Evidence: .sisyphus/evidence/task-3-prompts-happy.txt

  Scenario: Code example is valid Python
    Tool: Bash (python3 -c)
    Preconditions: prompts module loaded
    Steps:
      1. python3 -c "from scenarios.quant.prompts import FACTOR_CODE_EXAMPLE; compile(FACTOR_CODE_EXAMPLE, '<string>', 'exec'); print('Valid Python')"
      2. Assert: prints "Valid Python" without SyntaxError
    Expected Result: Example code compiles without errors
    Failure Indicators: SyntaxError
    Evidence: .sisyphus/evidence/task-3-prompts-syntax.txt
  ```

  **Commit**: YES (groups with T1, T2)
  - Message: `feat(quant): add mock data, constants, and prompt templates`
  - Files: `scenarios/quant/prompts.py`
  - Pre-commit: N/A (no separate test file)

### Wave 2 — Metrics & Backtest Engine (After Wave 1, 3 parallel)

- [ ] 4. Metrics Computation Library + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_metrics.py` with tests:
    - `test_ic_perfect_correlation` — IC of identical series = 1.0
    - `test_ic_no_correlation` — IC of random series ≈ 0 (within tolerance)
    - `test_ic_negative_correlation` — IC of inverted series = -1.0
    - `test_icir_stable_ic` — high ICIR when IC is consistently positive
    - `test_icir_unstable_ic` — low ICIR when IC flips sign
    - `test_rank_ic` — Spearman correlation matches expected
    - `test_sharpe_positive_returns` — positive Sharpe for consistently positive returns
    - `test_sharpe_zero_returns` — Sharpe = 0 for zero excess returns
    - `test_mdd_known_drawdown` — MDD for known price series (e.g., [100, 80, 90, 70] → MDD = -30%)
    - `test_arr_known_return` — annualized return for known total return
    - `test_calmar_ratio` — Calmar = ARR / |MDD|
    - `test_compute_all_metrics` — compute_all_metrics returns dict with all 8 keys
    - `test_all_nan_factor` — all-NaN factor returns NaN metrics (not crash)
    - `test_constant_factor` — constant factor returns IC=0, ICIR=NaN
    - `test_single_day_data` — edge case: single day returns meaningful defaults
  - GREEN: Implement `scenarios/quant/metrics.py`:
    - `compute_ic(predicted: pd.Series, actual: pd.Series, dates: pd.Series) -> dict` — returns `{"ic_mean", "ic_std", "ic_series"}`
    - `compute_icir(ic_series: pd.Series) -> float` — `mean(IC) / std(IC)`
    - `compute_rank_ic(predicted, actual, dates) -> dict` — Spearman version
    - `compute_rank_icir(rank_ic_series) -> float`
    - `compute_sharpe(returns: pd.Series, risk_free=0.0) -> float` — `mean(excess) / std * sqrt(252)`
    - `compute_mdd(cumulative_returns: pd.Series) -> float` — max drawdown (negative number)
    - `compute_arr(cumulative_returns: pd.Series, n_days: int) -> float` — annualized return
    - `compute_calmar(arr: float, mdd: float) -> float` — `arr / abs(mdd)`
    - `compute_all_metrics(factor_values, actual_returns, dates, portfolio_returns) -> dict` — aggregator
    - Handle edge cases: all-NaN, constant, single-day, division by zero
  - REFACTOR: Use constants.py thresholds for pass/fail annotation

  **Must NOT do**:
  - ❌ Do NOT implement portfolio construction here (that's backtest.py's job)
  - ❌ Do NOT use external quant libraries (empyrical, pyfolio) — implement from scratch with numpy/pandas
  - ❌ Do NOT over-optimize for speed — correctness first

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Math-heavy computation with edge cases, needs careful implementation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Tasks 6, 9, 10
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `evaluation_service/service.py` — How the project's existing evaluation service computes scores; metrics.py is the quant equivalent

  **API/Type References**:
  - `data_models.py:Score` — `Score(score_id, value, metric_name, details)` — our metrics dict will be converted to Score objects by the Runner/FeedbackAnalyzer
  - `scenarios/quant/constants.py:METRIC_THRESHOLDS` — thresholds for each metric (Task 2)

  **External References**:
  - IC formula: `pearson_corr(predicted_return_t, actual_return_t)` computed per cross-section (per date), then averaged
  - Sharpe: `(mean(r) - rf) / std(r) * sqrt(252)` where r = daily returns
  - MDD: `min(cumulative_wealth / running_max - 1)` over entire series
  - ARR: `(final_wealth / initial_wealth) ^ (252 / n_trading_days) - 1`

  **WHY Each Reference Matters**:
  - Score dataclass shows the exact format our metrics must convert to for compatibility with EvaluationService
  - IC is computed per cross-section (all stocks on one date), NOT per time series — this is a common mistake

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_metrics.py`
  - [ ] `python3 -m pytest tests/test_quant_metrics.py -q` → PASS (≥15 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Compute metrics on known data
    Tool: Bash (python3 -c)
    Preconditions: scenarios/quant/metrics.py exists
    Steps:
      1. python3 -c "
         import pandas as pd; import numpy as np
         from scenarios.quant.metrics import compute_all_metrics
         np.random.seed(42)
         n = 500
         dates = pd.date_range('2020-01-01', periods=n, freq='B')
         factor = pd.Series(np.random.randn(n))
         actual = factor * 0.1 + np.random.randn(n) * 0.5  # correlated
         port_returns = pd.Series(np.random.randn(n) * 0.01 + 0.0002)
         m = compute_all_metrics(factor, actual, dates, port_returns)
         print(f'IC: {m[\"ic_mean\"]:.4f}')
         print(f'Sharpe: {m[\"sharpe\"]:.4f}')
         print(f'MDD: {m[\"mdd\"]:.4f}')
         print(f'Keys: {sorted(m.keys())}')
         "
      2. Assert: IC > 0 (since factor and actual are positively correlated)
      3. Assert: Keys include all 8 metric names
    Expected Result: Positive IC, all metrics computed, no errors
    Failure Indicators: ImportError, NaN for non-edge-case data, missing keys
    Evidence: .sisyphus/evidence/task-4-metrics-happy.txt

  Scenario: All-NaN factor graceful handling
    Tool: Bash (python3 -c)
    Preconditions: metrics module loaded
    Steps:
      1. python3 -c "
         import pandas as pd; import numpy as np
         from scenarios.quant.metrics import compute_all_metrics
         dates = pd.date_range('2020-01-01', periods=10, freq='B')
         factor = pd.Series([np.nan]*10)
         actual = pd.Series(np.random.randn(10))
         port_returns = pd.Series([0.0]*10)
         m = compute_all_metrics(factor, actual, dates, port_returns)
         print(f'IC: {m[\"ic_mean\"]}')
         print('No crash - graceful handling')
         "
      2. Assert: prints "No crash" — no exception raised
    Expected Result: Returns NaN metrics without crashing
    Failure Indicators: Exception, crash
    Evidence: .sisyphus/evidence/task-4-metrics-nan.txt
  ```

  **Commit**: YES (groups with T5)
  - Message: `feat(quant): add metrics computation and code safety validator`
  - Files: `scenarios/quant/metrics.py`, `tests/test_quant_metrics.py`
  - Pre-commit: `pytest tests/test_quant_metrics.py -q`

- [ ] 5. Code Safety Validator + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_code_safety.py` with tests:
    - `test_valid_code_passes` — `import numpy as np; df['factor'] = df['close'].pct_change(5)` → passes
    - `test_os_import_blocked` — `import os` → rejected with reason
    - `test_subprocess_blocked` — `import subprocess` → rejected
    - `test_requests_blocked` — `import requests` → rejected
    - `test_exec_eval_blocked` — `exec("print(1)")` → rejected
    - `test_syntax_error_caught` — `def f(: pass` → rejected with "syntax error"
    - `test_from_import_blocked` — `from os import path` → rejected
    - `test_nested_import_blocked` — `__import__("os")` → rejected
    - `test_empty_code_rejected` — empty string → rejected
    - `test_open_file_blocked` — `open("/etc/passwd")` → rejected
  - GREEN: Implement `scenarios/quant/code_safety.py`:
    - `validate_code_safety(code: str) -> tuple[bool, Optional[str]]` — returns (is_safe, rejection_reason)
    - Step 1: AST parse (catch SyntaxError)
    - Step 2: Walk AST tree, check all Import/ImportFrom nodes against BLOCKED_IMPORTS
    - Step 3: Check for dangerous builtins: exec, eval, compile, __import__, open, globals, locals
    - Step 4: Check for attribute access on blocked modules (os.path, sys.exit)
    - Use constants.py BLOCKED_IMPORTS and SAFE_IMPORTS
  - REFACTOR: Ensure validation messages are descriptive

  **Must NOT do**:
  - ❌ Do NOT implement a full sandbox — just static analysis of the code string
  - ❌ Do NOT be overly restrictive — numpy, pandas, math, statistics must be allowed
  - ❌ Do NOT execute the code during validation — AST analysis only

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-purpose AST walking module, well-defined scope
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6)
  - **Blocks**: Tasks 8, 9
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - Python `ast` module: `ast.parse()`, `ast.walk()`, `ast.Import`, `ast.ImportFrom`, `ast.Call`

  **API/Type References**:
  - `scenarios/quant/constants.py:SAFE_IMPORTS, BLOCKED_IMPORTS` — import whitelist/blacklist (Task 2)

  **WHY Each Reference Matters**:
  - AST-based checking is the standard approach for safe code validation — we check the syntax tree, not string matching (which can be bypassed)

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_code_safety.py`
  - [ ] `python3 -m pytest tests/test_quant_code_safety.py -q` → PASS (≥10 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Valid factor code passes safety check
    Tool: Bash (python3 -c)
    Preconditions: scenarios/quant/code_safety.py exists
    Steps:
      1. python3 -c "
         from scenarios.quant.code_safety import validate_code_safety
         code = 'import numpy as np\nimport pandas as pd\ndef compute_factor(df):\n    return df.groupby(\"stock_id\")[\"close\"].pct_change(5)'
         is_safe, reason = validate_code_safety(code)
         print(f'Safe: {is_safe}, Reason: {reason}')
         "
      2. Assert: Safe: True, Reason: None
    Expected Result: Valid code with numpy/pandas passes
    Failure Indicators: is_safe=False for valid code
    Evidence: .sisyphus/evidence/task-5-safety-happy.txt

  Scenario: Dangerous import is blocked
    Tool: Bash (python3 -c)
    Preconditions: code_safety module loaded
    Steps:
      1. python3 -c "
         from scenarios.quant.code_safety import validate_code_safety
         code = 'import os\nos.system(\"rm -rf /\")'
         is_safe, reason = validate_code_safety(code)
         print(f'Safe: {is_safe}, Reason: {reason}')
         "
      2. Assert: Safe: False, Reason contains "os" or "blocked"
    Expected Result: Dangerous code is rejected with descriptive reason
    Failure Indicators: is_safe=True for dangerous code
    Evidence: .sisyphus/evidence/task-5-safety-blocked.txt
  ```

  **Commit**: YES (groups with T4)
  - Message: `feat(quant): add metrics computation and code safety validator`
  - Files: `scenarios/quant/code_safety.py`, `tests/test_quant_code_safety.py`
  - Pre-commit: `pytest tests/test_quant_code_safety.py -q`

- [ ] 6. Backtest Engine + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_backtest.py` with tests:
    - `test_backtest_basic_run` — runs without error on mock data + simple factor
    - `test_backtest_returns_shape` — returns portfolio_returns Series with correct length (test period only)
    - `test_backtest_train_test_split` — only computes metrics on test period data
    - `test_backtest_commission_deducted` — with commission > 0, returns are lower than without
    - `test_backtest_no_forward_looking` — factor signal on day T only uses data from ≤ day T
    - `test_backtest_portfolio_weights_sum_to_one` — weights normalized
    - `test_backtest_all_nan_factor` — returns empty/zero portfolio returns (no crash)
    - `test_backtest_constant_factor` — equal-weight portfolio (all stocks same factor value)
    - `test_backtest_known_factor` — known momentum factor produces positive returns on trending mock data
    - `test_backtest_metrics_included` — result dict includes all 8 metrics
    - `test_backtest_result_json_serializable` — result can be json.dumps'd
    - `test_backtest_respects_config` — uses BACKTEST_CONFIG for train/test dates, commission
  - GREEN: Implement `scenarios/quant/backtest.py`:
    - `class LightweightBacktester`:
      - `__init__(self, config: dict = None)` — uses BACKTEST_CONFIG defaults
      - `run(self, ohlcv_data: pd.DataFrame, factor_code: str) -> dict` — main entry point
        1. Execute factor_code safely (in restricted scope) to get factor_values
        2. Split data into train/test periods based on config dates
        3. On test period: for each rebalance date, rank stocks by factor_value
        4. Construct long-only portfolio: top N stocks (N = n_stocks // 5) equal-weighted
        5. Compute daily portfolio returns (accounting for commission + slippage)
        6. Call `compute_all_metrics()` on results
        7. Return `{"portfolio_returns": [...], "metrics": {...}, "positions": [...], "status": "success"}`
      - `_execute_factor_code(self, code: str, data: pd.DataFrame) -> pd.DataFrame` — execute in restricted namespace
      - `_construct_portfolio(self, factor_values: pd.DataFrame, date: str) -> dict` — stock_id → weight
      - `_compute_daily_returns(self, positions: list, ohlcv: pd.DataFrame) -> pd.Series`
    - Design principle: factor signal on day T uses data ≤ T, portfolio constructed at close of T, returns measured T+1
    - Commission/slippage deducted on each rebalance from position delta (turnover-based)

  **Must NOT do**:
  - ❌ Do NOT support short selling (long-only portfolio in v1)
  - ❌ Do NOT implement intraday trading logic
  - ❌ Do NOT add external backtesting library dependencies
  - ❌ Do NOT implement order book simulation
  - ❌ Do NOT implement adaptive position sizing (equal-weight only)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core computation engine with complex date handling, portfolio construction, and financial math
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 1, 2, 4

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:280-340` — How the data_science Runner executes generated code and collects results; backtest.py follows similar "execute code → collect output → format result" pattern
  - `scenarios/synthetic_research/plugin.py:350-400` — How synthetic_research Runner formats ExecutionResult — follow JSON serializable result pattern

  **API/Type References**:
  - `scenarios/quant/metrics.py:compute_all_metrics` — called by backtest engine to compute final metrics (Task 4)
  - `scenarios/quant/code_safety.py:validate_code_safety` — called before executing factor code (Task 5)
  - `scenarios/quant/mock_data.py:generate_ohlcv` — used in tests to create input data (Task 1)
  - `scenarios/quant/constants.py:BACKTEST_CONFIG` — default configuration (Task 2)

  **External References**:
  - Factor-based portfolio construction: rank stocks by factor → top quintile → equal weight
  - Turnover-based cost model: `cost = commission * sum(|weight_new - weight_old|)`
  - No-lookahead: signal[T] uses price[≤T], portfolio constructed at close[T], return measured at close[T+1]

  **WHY Each Reference Matters**:
  - data_science Runner shows how to execute LLM-generated code safely and capture results — backtest.py extends this pattern to financial domain
  - The no-lookahead constraint is THE most important correctness requirement — getting this wrong makes all metrics meaningless

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_backtest.py`
  - [ ] `python3 -m pytest tests/test_quant_backtest.py -q` → PASS (≥12 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Run backtest with momentum factor
    Tool: Bash (python3 -c)
    Preconditions: backtest.py, mock_data.py, metrics.py all exist
    Steps:
      1. python3 -c "
         from scenarios.quant.backtest import LightweightBacktester
         from scenarios.quant.mock_data import generate_ohlcv
         data = generate_ohlcv(n_stocks=20, n_days=200, seed=42)
         factor_code = '''
         import pandas as pd
         def compute_factor(df):
             result = df.copy()
             result['factor_value'] = df.groupby('stock_id')['close'].pct_change(5)
             return result[['date', 'stock_id', 'factor_value']]
         '''
         bt = LightweightBacktester()
         result = bt.run(data, factor_code)
         print(f'Status: {result[\"status\"]}')
         print(f'Metrics keys: {sorted(result[\"metrics\"].keys())}')
         print(f'Sharpe: {result[\"metrics\"][\"sharpe\"]:.4f}')
         print(f'IC: {result[\"metrics\"][\"ic_mean\"]:.4f}')
         "
      2. Assert: Status: success, all 8 metric keys present
    Expected Result: Backtest completes, metrics computed, no crash
    Failure Indicators: Exception, missing metrics, status != success
    Evidence: .sisyphus/evidence/task-6-backtest-happy.txt

  Scenario: Commission reduces returns
    Tool: Bash (python3 -c)
    Preconditions: backtest engine loaded
    Steps:
      1. python3 -c "
         from scenarios.quant.backtest import LightweightBacktester
         from scenarios.quant.mock_data import generate_ohlcv
         data = generate_ohlcv(n_stocks=10, n_days=100, seed=42)
         code = 'import pandas as pd\ndef compute_factor(df):\n    r = df.copy()\n    r[\"factor_value\"] = df.groupby(\"stock_id\")[\"close\"].pct_change(5)\n    return r[[\"date\",\"stock_id\",\"factor_value\"]]'
         bt_no_cost = LightweightBacktester({'commission_rate': 0.0, 'slippage_rate': 0.0})
         bt_with_cost = LightweightBacktester({'commission_rate': 0.01, 'slippage_rate': 0.01})
         r1 = bt_no_cost.run(data, code)
         r2 = bt_with_cost.run(data, code)
         print(f'No cost ARR: {r1[\"metrics\"][\"arr\"]:.4f}')
         print(f'With cost ARR: {r2[\"metrics\"][\"arr\"]:.4f}')
         print(f'Cost reduces returns: {r2[\"metrics\"][\"arr\"] < r1[\"metrics\"][\"arr\"]}')
         "
      2. Assert: "Cost reduces returns: True"
    Expected Result: Higher commission → lower returns
    Failure Indicators: Cost has no effect on returns
    Evidence: .sisyphus/evidence/task-6-backtest-commission.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(quant): add lightweight backtest engine`
  - Files: `scenarios/quant/backtest.py`, `tests/test_quant_backtest.py`
  - Pre-commit: `pytest tests/test_quant_backtest.py -q`

### Wave 3 — Plugin Components (After Wave 2, 5 parallel)

- [ ] 7. ScenarioPlugin + ProposalEngine + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_plugin_scenario.py` with tests:
    - `test_build_context_returns_scenario_context` — returns ScenarioContext with correct scenario_name="quant"
    - `test_build_context_propagates_step_config` — step_config from input_payload is preserved
    - `test_build_context_sets_task_summary` — task_summary populated from payload or default
    - `test_propose_returns_proposal` — returns Proposal dataclass with valid fields
    - `test_propose_includes_factor_hypothesis` — proposal.description contains factor-related content
    - `test_propose_uses_previous_feedback` — when context includes feedback, proposal references it
    - `test_propose_with_empty_context` — works when no prior history
  - GREEN: Implement in `scenarios/quant/plugin.py`:
    - `class QuantScenarioPlugin` (implements ScenarioPlugin Protocol):
      - `def build_context(self, run_session, input_payload) -> ScenarioContext`
        - Extract task_summary from payload (default: "Mine alpha factors for stock return prediction")
        - Extract/create StepOverrideConfig from payload
        - Return ScenarioContext(run_id, scenario_name="quant", input_payload, task_summary, step_config)
    - `class QuantProposalEngine` (implements ProposalEngine Protocol):
      - `__init__(self, llm_adapter=None)`
      - `def propose(self, task_summary, context, parent_ids, plan, scenario) -> Proposal`
        - Use FACTOR_PROPOSAL_SYSTEM_PROMPT + FACTOR_PROPOSAL_USER_TEMPLATE
        - If llm_adapter is None: return a mock Proposal with a simple momentum hypothesis
        - If llm_adapter exists: call llm_adapter.generate_structured() to get factor hypothesis
        - Return Proposal(proposal_id=uuid, description=hypothesis, parent_ids=parent_ids)

  **Must NOT do**:
  - ❌ Do NOT implement complex multi-factor proposal logic
  - ❌ Do NOT call external APIs in build_context
  - ❌ Do NOT modify ScenarioContext structure — use existing dataclass exactly

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Plugin protocol implementation requiring careful interface adherence
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 9, 10, 11)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 1, 2, 3

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:35-100` — DataScienceScenarioPlugin.build_context() implementation — follow EXACTLY the same pattern for step_config propagation
  - `scenarios/data_science/plugin.py:100-170` — DataScienceProposalEngine.propose() — follow the llm_adapter fallback pattern (mock when None)
  - `scenarios/synthetic_research/plugin.py:30-90` — SyntheticResearchScenarioPlugin — second reference for build_context pattern

  **API/Type References**:
  - `plugins/contracts.py:ScenarioContext` — exact dataclass to return from build_context
  - `plugins/contracts.py:ScenarioPlugin` — Protocol to implement
  - `plugins/contracts.py:ProposalEngine` — Protocol to implement
  - `data_models.py:Proposal` — return type of propose() (fields: proposal_id, description, parent_ids, metadata)
  - `data_models.py:RunSession` — input to build_context
  - `service_contracts.py:StepOverrideConfig` — must be propagated via step_config field
  - `scenarios/quant/prompts.py:FACTOR_PROPOSAL_*` — prompt templates (Task 3)

  **WHY Each Reference Matters**:
  - data_science build_context is the canonical example — step_config propagation must match EXACTLY or StepExecutor breaks
  - Proposal dataclass fields must be populated correctly — StepExecutor reads proposal.description for downstream steps

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_plugin_scenario.py`
  - [ ] `python3 -m pytest tests/test_quant_plugin_scenario.py -q` → PASS (≥7 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Build context with default payload
    Tool: Bash (python3 -c)
    Preconditions: scenarios/quant/plugin.py exists with QuantScenarioPlugin
    Steps:
      1. python3 -c "
         from scenarios.quant.plugin import QuantScenarioPlugin
         from data_models import RunSession
         sp = QuantScenarioPlugin()
         ctx = sp.build_context(RunSession(run_id='test-1', scenario='quant', config={}), {'task_summary': 'test quant'})
         print(f'scenario_name: {ctx.scenario_name}')
         print(f'run_id: {ctx.run_id}')
         print(f'task_summary: {ctx.task_summary}')
         print(f'has step_config: {ctx.step_config is not None}')
         "
      2. Assert: scenario_name: quant, run_id: test-1, task_summary: test quant, has step_config: True
    Expected Result: ScenarioContext correctly constructed
    Failure Indicators: Wrong scenario_name, missing step_config
    Evidence: .sisyphus/evidence/task-7-scenario-happy.txt

  Scenario: Propose without LLM adapter (mock mode)
    Tool: Bash (python3 -c)
    Preconditions: QuantProposalEngine exists
    Steps:
      1. python3 -c "
         from scenarios.quant.plugin import QuantProposalEngine
         from plugins.contracts import ScenarioContext
         from service_contracts import StepOverrideConfig
         pe = QuantProposalEngine(llm_adapter=None)
         ctx = ScenarioContext(run_id='t', scenario_name='quant', input_payload={}, task_summary='test', step_config=StepOverrideConfig())
         from data_models import Plan
         from memory_service.context_pack import ContextPack
         proposal = pe.propose('mine factors', ContextPack(), [], Plan(plan_id='p', steps=[]), ctx)
         print(f'proposal_id: {proposal.proposal_id}')
         print(f'description length: {len(proposal.description)}')
         print(f'has content: {len(proposal.description) > 10}')
         "
      2. Assert: proposal_id is non-empty, description > 10 chars
    Expected Result: Mock proposal generated without LLM
    Failure Indicators: Exception, empty proposal
    Evidence: .sisyphus/evidence/task-7-proposal-mock.txt
  ```

  **Commit**: YES (groups with T8, T9, T10, T11)
  - Message: `feat(quant): implement full plugin bundle (scenario, proposal, coder, runner, feedback)`
  - Files: `scenarios/quant/plugin.py`, `tests/test_quant_plugin_scenario.py`
  - Pre-commit: `pytest tests/test_quant_plugin_scenario.py -q`

- [ ] 8. ExperimentGenerator + Coder + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_plugin_coder.py` with tests:
    - `test_generate_returns_experiment_node` — returns ExperimentNode with valid fields
    - `test_generate_sets_workspace_ref` — workspace_ref is a valid path string
    - `test_generate_node_id_unique` — two calls produce different node_ids
    - `test_develop_returns_code_artifact` — returns CodeArtifact
    - `test_develop_writes_factor_code_to_workspace` — factor.py file created in workspace
    - `test_develop_writes_runner_script` — run_backtest.py script created in workspace
    - `test_develop_code_passes_safety_check` — generated code passes validate_code_safety
    - `test_develop_without_llm_generates_mock_code` — when llm_adapter=None, generates a default momentum factor
  - GREEN: Implement in `scenarios/quant/plugin.py`:
    - `class QuantExperimentGenerator` (implements ExperimentGenerator Protocol):
      - `def generate(self, proposal, run_session, loop_state, parent_ids) -> ExperimentNode`
        - Create node_id = f"quant-{uuid4().hex[:8]}"
        - Set workspace_ref = os.path.join(workspace_root, run_session.run_id, node_id)
        - Return ExperimentNode(node_id, workspace_ref, ...)
    - `class QuantCoder` (implements Coder Protocol):
      - `__init__(self, llm_adapter=None)`
      - `def develop(self, experiment, proposal, scenario) -> CodeArtifact`
        - If llm_adapter: use FACTOR_CODE_SYSTEM_PROMPT + proposal.description to generate factor code
        - If no llm_adapter: generate default momentum factor code (from FACTOR_CODE_EXAMPLE)
        - Validate code safety via validate_code_safety()
        - Write to workspace:
          - `factor.py` — the factor computation code
          - `run_backtest.py` — script that loads data, runs factor, calls backtest, saves results to metrics.json
          - `README.md` — description of the factor hypothesis
        - Return CodeArtifact(artifact_id=uuid, description=proposal.description, location=experiment.workspace_ref)

  **Must NOT do**:
  - ❌ Do NOT implement CoSTEER multi-round coding evolution (v1 is single-round)
  - ❌ Do NOT execute code in the Coder — that's the Runner's job
  - ❌ Do NOT validate factor results in Coder — that's FeedbackAnalyzer's job

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Plugin protocol + file I/O + LLM integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 7, 9, 10, 11)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 1, 2, 3, 5

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:170-250` — DataScienceExperimentGenerator + DataScienceCoder — follow EXACTLY for workspace file writing pattern
  - `scenarios/synthetic_research/plugin.py:170-280` — SyntheticResearchCoder — second reference for how artifacts are structured

  **API/Type References**:
  - `plugins/contracts.py:ExperimentGenerator` — Protocol
  - `plugins/contracts.py:Coder` — Protocol
  - `data_models.py:ExperimentNode` — return type (fields: node_id, workspace_ref, result_ref, branch_id, parent_node_id, step_state)
  - `data_models.py:CodeArtifact` — return type (fields: artifact_id, description, location)
  - `scenarios/quant/code_safety.py:validate_code_safety` — safety check before writing code (Task 5)
  - `scenarios/quant/prompts.py:FACTOR_CODE_*` — code generation prompts (Task 3)

  **WHY Each Reference Matters**:
  - data_science Coder shows exactly how to write files to workspace_ref and return CodeArtifact.location — Runner depends on this exact path structure
  - CodeArtifact.location MUST equal experiment.workspace_ref — the Runner reads from this path

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_plugin_coder.py`
  - [ ] `python3 -m pytest tests/test_quant_plugin_coder.py -q` → PASS (≥8 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Generate experiment and develop code
    Tool: Bash (python3 -c)
    Preconditions: plugin.py has QuantExperimentGenerator and QuantCoder
    Steps:
      1. python3 -c "
         import tempfile, os, json
         from scenarios.quant.plugin import QuantExperimentGenerator, QuantCoder
         from data_models import Proposal, RunSession, ExperimentNode
         from plugins.contracts import ScenarioContext
         from service_contracts import StepOverrideConfig
         from core.loop.step_executor import LoopState
         # Setup
         gen = QuantExperimentGenerator(workspace_root=tempfile.mkdtemp())
         proposal = Proposal(proposal_id='p1', description='5-day momentum factor', parent_ids=[], metadata={})
         rs = RunSession(run_id='test-run', scenario='quant', config={})
         ls = LoopState(iteration=0, max_iterations=3)
         exp = gen.generate(proposal, rs, ls, [])
         print(f'node_id: {exp.node_id}')
         print(f'workspace exists: {os.path.isdir(exp.workspace_ref)}')
         # Develop
         coder = QuantCoder(llm_adapter=None)
         ctx = ScenarioContext(run_id='test-run', scenario_name='quant', input_payload={}, task_summary='test', step_config=StepOverrideConfig())
         artifact = coder.develop(exp, proposal, ctx)
         print(f'artifact location: {os.path.isdir(artifact.location)}')
         print(f'factor.py exists: {os.path.isfile(os.path.join(artifact.location, \"factor.py\"))}')
         print(f'run_backtest.py exists: {os.path.isfile(os.path.join(artifact.location, \"run_backtest.py\"))}')
         "
      2. Assert: node_id non-empty, workspace exists, factor.py exists, run_backtest.py exists
    Expected Result: Full code generation pipeline works in mock mode
    Failure Indicators: Missing files, wrong paths
    Evidence: .sisyphus/evidence/task-8-coder-happy.txt

  Scenario: Generated code passes safety check
    Tool: Bash (python3 -c)
    Preconditions: coder produces factor.py
    Steps:
      1. python3 -c "
         import tempfile
         from scenarios.quant.plugin import QuantExperimentGenerator, QuantCoder
         from scenarios.quant.code_safety import validate_code_safety
         from data_models import Proposal, RunSession
         from plugins.contracts import ScenarioContext
         from service_contracts import StepOverrideConfig
         from core.loop.step_executor import LoopState
         gen = QuantExperimentGenerator(workspace_root=tempfile.mkdtemp())
         proposal = Proposal(proposal_id='p1', description='test', parent_ids=[], metadata={})
         rs = RunSession(run_id='t', scenario='quant', config={})
         exp = gen.generate(proposal, rs, LoopState(iteration=0, max_iterations=1), [])
         coder = QuantCoder(llm_adapter=None)
         ctx = ScenarioContext(run_id='t', scenario_name='quant', input_payload={}, task_summary='t', step_config=StepOverrideConfig())
         artifact = coder.develop(exp, proposal, ctx)
         import os
         code = open(os.path.join(artifact.location, 'factor.py')).read()
         is_safe, reason = validate_code_safety(code)
         print(f'Safe: {is_safe}, Reason: {reason}')
         "
      2. Assert: Safe: True
    Expected Result: Default generated code is safe
    Failure Indicators: Safety check fails on our own generated code
    Evidence: .sisyphus/evidence/task-8-coder-safety.txt
  ```

  **Commit**: YES (groups with T7, T9, T10, T11)
  - Message: `feat(quant): implement full plugin bundle`
  - Files: `scenarios/quant/plugin.py` (additions), `tests/test_quant_plugin_coder.py`
  - Pre-commit: `pytest tests/test_quant_plugin_coder.py -q`

- [ ] 9. Runner (wraps backtest engine) + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_plugin_runner.py` with tests:
    - `test_run_returns_execution_result` — returns ExecutionResult with correct fields
    - `test_run_exit_code_zero_on_success` — exit_code=0 for valid factor
    - `test_run_exit_code_nonzero_on_failure` — exit_code=1 for invalid/crashing factor
    - `test_run_artifacts_ref_is_json_list` — json.loads(result.artifacts_ref) is a list
    - `test_run_logs_ref_contains_output` — logs_ref has stdout/stderr content
    - `test_run_artifact_manifest_has_paths` — artifact_manifest includes metrics.json path
    - `test_run_metrics_json_written` — metrics.json file exists in workspace after run
    - `test_run_timeout_handling` — factor that takes too long returns timed_out=True
    - `test_run_syntax_error_handling` — factor with syntax error returns gracefully
  - GREEN: Implement in `scenarios/quant/plugin.py`:
    - `class QuantRunner` (implements Runner Protocol):
      - `__init__(self, execution_backend=None, mock_data_generator=None)`
      - `def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult`
        1. Read `factor.py` from artifact.location
        2. Validate code safety → if unsafe, return ExecutionResult(exit_code=1, logs_ref="Unsafe code: {reason}")
        3. Load/generate mock OHLCV data (use mock_data_generator or default generate_ohlcv())
        4. Create LightweightBacktester with scenario config
        5. Run backtest: `backtester.run(data, factor_code)`
        6. Write results to `metrics.json` in workspace
        7. Return ExecutionResult:
           - run_id from scenario
           - exit_code = 0 if success, 1 if failure
           - logs_ref = backtest stdout/logs
           - artifacts_ref = json.dumps(["metrics.json"]) ← CRITICAL FORMAT
           - artifact_manifest = {"paths": ["metrics.json"], ...}
           - duration_sec = measured execution time
        - Handle exceptions gracefully: catch all, return exit_code=1 with error in logs_ref
      - If execution_backend is provided: delegate to DockerExecutionBackend.execute() instead
      - If execution_backend is None: run locally in-process (for testing)

  **Must NOT do**:
  - ❌ Do NOT compute metrics in Runner — delegate to LightweightBacktester which uses metrics.py
  - ❌ Do NOT modify the ExecutionResult dataclass — use it as-is
  - ❌ Do NOT silently swallow errors — always include error details in logs_ref

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Critical integration point between Coder output and ExecutionResult contract
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 7, 8, 10, 11)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 1, 2, 4, 5, 6

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:250-340` — DataScienceRunner.run() — FOLLOW THIS EXACTLY for ExecutionResult construction, especially artifacts_ref format
  - `scenarios/synthetic_research/plugin.py:300-370` — SyntheticResearchRunner.run() — second reference for how to handle local execution fallback

  **API/Type References**:
  - `plugins/contracts.py:Runner` — Protocol to implement
  - `data_models.py:ExecutionResult` — return type (CRITICAL: artifacts_ref must be json.dumps(list))
  - `data_models.py:CodeArtifact` — input (artifact.location = workspace path)
  - `data_models.py:ExecutionOutcomeContract` — optional outcome field
  - `scenarios/quant/backtest.py:LightweightBacktester` — the actual backtest engine (Task 6)
  - `scenarios/quant/code_safety.py:validate_code_safety` — pre-run safety check (Task 5)
  - `scenarios/quant/mock_data.py:generate_ohlcv` — data source (Task 1)
  - `core/execution/backend.py:ExecutionBackend, BackendResult` — if delegating to Docker

  **WHY Each Reference Matters**:
  - DataScienceRunner shows the EXACT pattern for artifacts_ref = json.dumps([...]) — CommonUsefulnessGate will parse this and BREAK if format is wrong
  - ExecutionResult.resolve_outcome() depends on artifacts_ref being valid JSON — this is the #1 integration failure point

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_plugin_runner.py`
  - [ ] `python3 -m pytest tests/test_quant_plugin_runner.py -q` → PASS (≥9 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Run valid factor and get metrics
    Tool: Bash (python3 -c)
    Preconditions: Runner, Coder, mock_data all available
    Steps:
      1. python3 -c "
         import tempfile, os, json
         from scenarios.quant.plugin import QuantExperimentGenerator, QuantCoder, QuantRunner
         from data_models import Proposal, RunSession
         from plugins.contracts import ScenarioContext
         from service_contracts import StepOverrideConfig
         from core.loop.step_executor import LoopState
         # Setup workspace and code
         gen = QuantExperimentGenerator(workspace_root=tempfile.mkdtemp())
         rs = RunSession(run_id='t', scenario='quant', config={})
         proposal = Proposal(proposal_id='p1', description='momentum', parent_ids=[], metadata={})
         exp = gen.generate(proposal, rs, LoopState(iteration=0, max_iterations=1), [])
         coder = QuantCoder(llm_adapter=None)
         ctx = ScenarioContext(run_id='t', scenario_name='quant', input_payload={}, task_summary='t', step_config=StepOverrideConfig())
         artifact = coder.develop(exp, proposal, ctx)
         # Run
         runner = QuantRunner()
         result = runner.run(artifact, ctx)
         print(f'exit_code: {result.exit_code}')
         print(f'artifacts_ref valid JSON: {type(json.loads(result.artifacts_ref)) == list}')
         print(f'logs_ref non-empty: {len(result.logs_ref) > 0}')
         print(f'metrics.json exists: {os.path.isfile(os.path.join(artifact.location, \"metrics.json\"))}')
         "
      2. Assert: exit_code: 0, artifacts_ref valid JSON list, metrics.json exists
    Expected Result: Runner executes backtest and produces results
    Failure Indicators: exit_code != 0, artifacts_ref not JSON, missing metrics.json
    Evidence: .sisyphus/evidence/task-9-runner-happy.txt

  Scenario: Invalid code returns error gracefully
    Tool: Bash (python3 -c)
    Preconditions: Runner available
    Steps:
      1. python3 -c "
         import tempfile, os
         from scenarios.quant.plugin import QuantRunner
         from data_models import CodeArtifact
         from plugins.contracts import ScenarioContext
         from service_contracts import StepOverrideConfig
         # Write bad code to workspace
         ws = tempfile.mkdtemp()
         with open(os.path.join(ws, 'factor.py'), 'w') as f:
             f.write('import os\nos.system(\"rm -rf /\")')
         artifact = CodeArtifact(artifact_id='bad', description='bad', location=ws)
         ctx = ScenarioContext(run_id='t', scenario_name='quant', input_payload={}, task_summary='t', step_config=StepOverrideConfig())
         runner = QuantRunner()
         result = runner.run(artifact, ctx)
         print(f'exit_code: {result.exit_code}')
         print(f'logs mention unsafe: {\"nsafe\" in result.logs_ref or \"locked\" in result.logs_ref.lower()}')
         "
      2. Assert: exit_code != 0, logs mention safety issue
    Expected Result: Unsafe code detected and rejected gracefully
    Failure Indicators: exit_code=0 for unsafe code, or exception instead of graceful handling
    Evidence: .sisyphus/evidence/task-9-runner-unsafe.txt
  ```

  **Commit**: YES (groups with T7, T8, T10, T11)
  - Message: `feat(quant): implement full plugin bundle`
  - Files: `scenarios/quant/plugin.py` (additions), `tests/test_quant_plugin_runner.py`
  - Pre-commit: `pytest tests/test_quant_plugin_runner.py -q`

- [ ] 10. FeedbackAnalyzer + UsefulnessGateValidator + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_plugin_feedback.py` with tests:
    - `test_summarize_returns_feedback_record` — returns FeedbackRecord with valid fields
    - `test_summarize_decision_true_for_good_metrics` — Sharpe > threshold → decision=True
    - `test_summarize_decision_false_for_bad_metrics` — Sharpe < threshold → decision=False
    - `test_summarize_includes_all_metrics_in_observations` — observations field contains metric values
    - `test_summarize_reason_explains_result` — reason field is descriptive
    - `test_summarize_handles_no_score` — works when score=None
    - `test_usefulness_validator_passes_valid_result` — valid metrics.json → returns None
    - `test_usefulness_validator_rejects_missing_metrics` — no metrics.json → returns rejection string
    - `test_usefulness_validator_rejects_nan_metrics` — all-NaN metrics → returns rejection string
    - `test_usefulness_validator_rejects_empty_artifacts` — empty artifact_texts → rejection
  - GREEN: Implement in `scenarios/quant/plugin.py`:
    - `class QuantFeedbackAnalyzer` (implements FeedbackAnalyzer Protocol):
      - `__init__(self, llm_adapter=None)`
      - `def summarize(self, experiment, result, score=None) -> FeedbackRecord`
        1. Parse metrics from result.artifacts_ref or artifact files
        2. Evaluate primary metric (Sharpe) against threshold
        3. Evaluate constraint metrics (IC, ICIR, MDD) against thresholds
        4. Set decision = True if primary metric passes AND all constraints pass
        5. Set acceptable = decision (same logic)
        6. Format observations with all 8 metric values and pass/fail status
        7. Format reason: "Factor achieved Sharpe={X} (threshold={Y}). IC={Z}, MDD={W}..."
        8. If llm_adapter: additionally generate improvement suggestions
        9. Return FeedbackRecord(feedback_id, decision, acceptable, reason, observations, code_change_summary)
    - `def validate_quant_usefulness(gate_input: UsefulnessGateInput) -> Optional[str]`
      - Check gate_input.artifact_texts contains a metrics.json-like file
      - Parse the JSON, verify required metric keys exist
      - Check for all-NaN or nonsensical values (e.g., Sharpe = Inf)
      - Check for constant factor (IC = exactly 0.0)
      - Return None if valid, return rejection reason string if not

  **Must NOT do**:
  - ❌ Do NOT implement complex multi-objective optimization — simple threshold-based pass/fail
  - ❌ Do NOT modify FeedbackRecord structure — use existing dataclass
  - ❌ Do NOT make validator too strict — LLM factors may start weak and improve

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Two protocol implementations + careful threshold logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 7, 8, 9, 11)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 1, 2, 4

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:340-430` — DataScienceFeedbackAnalyzer — follow pattern for FeedbackRecord construction
  - `scenarios/data_science/plugin.py:430-470` — _validate_data_science_usefulness — follow EXACTLY for scene_usefulness_validator pattern (return None=pass, str=reject)
  - `scenarios/synthetic_research/plugin.py:400-500` — SyntheticResearchFeedbackAnalyzer + validator

  **API/Type References**:
  - `plugins/contracts.py:FeedbackAnalyzer` — Protocol to implement
  - `plugins/contracts.py:UsefulnessGateInput` — dataclass with fields: scenario, result, artifact_paths, artifact_texts, normalized_text, structured_payload
  - `plugins/contracts.py:CommonUsefulnessGate` — calls scene_validator after its own checks
  - `data_models.py:FeedbackRecord` — return type (fields: feedback_id, decision, acceptable, reason, observations, code_change_summary)
  - `scenarios/quant/constants.py:METRIC_THRESHOLDS, PRIMARY_METRIC, CONSTRAINT_METRICS` — thresholds (Task 2)

  **WHY Each Reference Matters**:
  - _validate_data_science_usefulness is the exact pattern — scene_validator receives UsefulnessGateInput (not raw ExecutionResult), must parse artifact_texts to find metrics
  - FeedbackRecord.decision and .acceptable are both used by StepExecutor — must be set correctly for the loop to function

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_plugin_feedback.py`
  - [ ] `python3 -m pytest tests/test_quant_plugin_feedback.py -q` → PASS (≥10 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Good metrics produce positive feedback
    Tool: Bash (python3 -c)
    Preconditions: FeedbackAnalyzer and validator exist
    Steps:
      1. python3 -c "
         import json
         from scenarios.quant.plugin import QuantFeedbackAnalyzer
         from data_models import ExperimentNode, ExecutionResult
         exp = ExperimentNode(node_id='n1', workspace_ref='/tmp/test', result_ref='')
         good_metrics = {'sharpe': 1.5, 'ic_mean': 0.05, 'icir': 0.8, 'mdd': -0.15, 'arr': 0.12, 'calmar': 3.0, 'rank_ic_mean': 0.04, 'rank_icir': 0.6}
         result = ExecutionResult(run_id='t', exit_code=0, logs_ref='ok', artifacts_ref=json.dumps(['metrics.json']), artifact_manifest={'metrics': good_metrics})
         fa = QuantFeedbackAnalyzer()
         fb = fa.summarize(exp, result)
         print(f'decision: {fb.decision}')
         print(f'acceptable: {fb.acceptable}')
         print(f'reason: {fb.reason[:80]}')
         "
      2. Assert: decision: True, acceptable: True
    Expected Result: Good metrics → positive feedback
    Failure Indicators: decision=False for good metrics
    Evidence: .sisyphus/evidence/task-10-feedback-good.txt

  Scenario: Usefulness validator rejects NaN metrics
    Tool: Bash (python3 -c)
    Preconditions: validate_quant_usefulness exists
    Steps:
      1. python3 -c "
         from scenarios.quant.plugin import validate_quant_usefulness
         from plugins.contracts import UsefulnessGateInput, ScenarioContext
         from data_models import ExecutionResult
         from service_contracts import StepOverrideConfig
         ctx = ScenarioContext(run_id='t', scenario_name='quant', input_payload={}, task_summary='t', step_config=StepOverrideConfig())
         result = ExecutionResult(run_id='t', exit_code=0, logs_ref='ok', artifacts_ref='[]')
         gate = UsefulnessGateInput(scenario=ctx, result=result, artifact_paths=[], artifact_texts={'metrics.json': '{\"sharpe\": NaN, \"ic_mean\": NaN}'}, normalized_text='', structured_payload=None)
         rejection = validate_quant_usefulness(gate)
         print(f'Rejected: {rejection is not None}')
         print(f'Reason: {rejection}')
         "
      2. Assert: Rejected: True, Reason mentions NaN or invalid
    Expected Result: NaN metrics are rejected
    Failure Indicators: Returns None (passes) for NaN metrics
    Evidence: .sisyphus/evidence/task-10-validator-nan.txt
  ```

  **Commit**: YES (groups with T7, T8, T9, T11)
  - Message: `feat(quant): implement full plugin bundle`
  - Files: `scenarios/quant/plugin.py` (additions), `tests/test_quant_plugin_feedback.py`
  - Pre-commit: `pytest tests/test_quant_plugin_feedback.py -q`

- [ ] 11. PluginBundle Assembly + Registry + Tests (TDD)

  **What to do**:
  - RED: Write `tests/test_quant_plugin_bundle.py` with tests:
    - `test_build_quant_bundle_returns_plugin_bundle` — returns PluginBundle instance
    - `test_bundle_scenario_name` — bundle.scenario_name == "quant"
    - `test_bundle_all_components_non_none` — all 6 components are set
    - `test_bundle_scene_validator_set` — scene_usefulness_validator is not None
    - `test_bundle_step_overrides_set` — default_step_overrides is a StepOverrideConfig
    - `test_registry_contains_quant` — build_default_registry includes "quant"
    - `test_registry_create_bundle_quant` — registry.create_bundle("quant") returns working PluginBundle
  - GREEN: Implement:
    - `scenarios/quant/__init__.py`:
      - `def build_quant_bundle(llm_adapter=None, execution_backend=None, **kwargs) -> PluginBundle`
        - Instantiate all 6 components
        - Return PluginBundle(scenario_name="quant", scenario_plugin=..., ..., scene_usefulness_validator=validate_quant_usefulness, default_step_overrides=StepOverrideConfig())
    - Modify `plugins/__init__.py` → `build_default_registry`:
      - Add `registry.register("quant", lambda: scenarios_module.build_quant_bundle(...))`
      - Import: `from scenarios.quant import build_quant_bundle`

  **Must NOT do**:
  - ❌ Do NOT modify PluginBundle dataclass — use it as-is
  - ❌ Do NOT change existing scenario registrations (data_science, synthetic_research must remain)
  - ❌ Do NOT modify core framework files (app/runtime.py, core/loop/*, etc.)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Wiring/glue code — straightforward assembly
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (end of Wave 3)
  - **Blocks**: Tasks 12, 13
  - **Blocked By**: Tasks 7, 8, 9, 10

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:1-30` + `scenarios/data_science/__init__.py` — How data_science exports build_data_science_v1_bundle; follow EXACTLY
  - `plugins/__init__.py:build_default_registry` — Where to add the "quant" registration line
  - `scenarios/__init__.py` — How scenarios package exposes bundles

  **API/Type References**:
  - `plugins/contracts.py:PluginBundle` — the final assembly dataclass
  - `plugins/registry.py:PluginRegistry` — register(name, factory) + create_bundle(name) API

  **WHY Each Reference Matters**:
  - build_default_registry is the ONLY place new scenarios are wired — missing this registration means the scenario can't be used at runtime
  - The lambda factory pattern (registry.register("quant", lambda: ...)) must match existing pattern exactly

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_plugin_bundle.py`
  - [ ] `python3 -m pytest tests/test_quant_plugin_bundle.py -q` → PASS (≥7 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Bundle loads via registry
    Tool: Bash (python3 -c)
    Preconditions: quant registered in build_default_registry
    Steps:
      1. python3 -c "
         from plugins import build_default_registry
         registry = build_default_registry()
         bundle = registry.create_bundle('quant')
         print(f'scenario_name: {bundle.scenario_name}')
         print(f'has scenario_plugin: {bundle.scenario_plugin is not None}')
         print(f'has proposal_engine: {bundle.proposal_engine is not None}')
         print(f'has runner: {bundle.runner is not None}')
         print(f'has feedback_analyzer: {bundle.feedback_analyzer is not None}')
         print(f'has validator: {bundle.scene_usefulness_validator is not None}')
         "
      2. Assert: scenario_name: quant, all components non-None
    Expected Result: Quant bundle instantiated from registry
    Failure Indicators: KeyError for "quant", any component is None
    Evidence: .sisyphus/evidence/task-11-bundle-registry.txt

  Scenario: Existing scenarios still work
    Tool: Bash (python3 -c)
    Preconditions: registry modified
    Steps:
      1. python3 -c "
         from plugins import build_default_registry
         registry = build_default_registry()
         ds = registry.create_bundle('data_science')
         sr = registry.create_bundle('synthetic_research')
         qt = registry.create_bundle('quant')
         print(f'data_science: {ds.scenario_name}')
         print(f'synthetic_research: {sr.scenario_name}')
         print(f'quant: {qt.scenario_name}')
         print('All 3 scenarios loaded successfully')
         "
      2. Assert: All 3 scenarios load without error
    Expected Result: No regression — existing scenarios unaffected
    Failure Indicators: ImportError, KeyError for existing scenarios
    Evidence: .sisyphus/evidence/task-11-bundle-no-regression.txt
  ```

  **Commit**: YES (groups with T7, T8, T9, T10)
  - Message: `feat(quant): implement full plugin bundle (scenario, proposal, coder, runner, feedback)`
  - Files: `scenarios/quant/__init__.py`, `plugins/__init__.py` (modified), `tests/test_quant_plugin_bundle.py`
  - Pre-commit: `pytest tests/test_quant_plugin_bundle.py -q`

### Wave 4 — Integration & Verification (After Wave 3, 2 parallel)

- [ ] 12. Full-Chain Integration Test (TDD)

  **What to do**:
  - Write `tests/test_quant_integration.py` — end-to-end test of the entire factor mining loop:
    - `test_full_chain_propose_to_feedback` — execute complete: build_context → propose → generate → develop → run → summarize
      - Use mock LLM (llm_adapter=None)
      - Verify each step returns correct type
      - Verify metrics.json is written
      - Verify FeedbackRecord has meaningful content
    - `test_full_chain_types_compatible` — verify type compatibility between all steps:
      - ScenarioContext from step 1 accepted by step 2-6
      - Proposal from step 2 accepted by step 3-4
      - ExperimentNode from step 3 accepted by step 4-5
      - CodeArtifact from step 4 accepted by step 5
      - ExecutionResult from step 5 accepted by step 6
    - `test_full_chain_usefulness_gate` — run CommonUsefulnessGate.evaluate on the ExecutionResult + scene_validator
      - Verify it returns ExecutionOutcomeContract + UsefulnessGateSignal
    - `test_full_chain_multiple_iterations` — run 2 iterations, verify second iteration can use feedback from first
    - `test_full_chain_with_real_step_executor` — (if feasible) create a StepExecutor with the quant PluginBundle and run execute_iteration

  **Must NOT do**:
  - ❌ Do NOT test with real LLM calls — mock mode only
  - ❌ Do NOT test Docker execution — local execution only
  - ❌ Do NOT make tests flaky (no network calls, no timing dependencies)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex integration test touching all components — needs deep understanding
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 13)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 11

  **References**:

  **Pattern References**:
  - `tests/test_task_02_plugin_contracts.py` — EXISTING integration test for plugin contracts — follow this EXACT pattern for test_full_chain_propose_to_feedback
  - `tests/test_integration_full_loop.py` — Existing full loop integration test
  - `core/loop/step_executor.py:execute_iteration` — The actual call sequence that will use our plugin in production

  **API/Type References**:
  - All plugin contracts from `plugins/contracts.py`
  - All data models from `data_models.py`
  - `plugins/contracts.py:CommonUsefulnessGate` — for usefulness gate testing
  - `core/loop/step_executor.py:StepExecutor` — for optional direct executor testing

  **WHY Each Reference Matters**:
  - test_task_02_plugin_contracts.py is THE reference for how integration tests work in this project — our test must be compatible with and similar to this
  - StepExecutor.execute_iteration is the real caller — our integration test simulates its exact call sequence

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_quant_integration.py`
  - [ ] `python3 -m pytest tests/test_quant_integration.py -q` → PASS (≥5 tests, 0 failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full chain execution
    Tool: Bash (python3 -m pytest)
    Preconditions: All quant modules implemented and registered
    Steps:
      1. python3 -m pytest tests/test_quant_integration.py -v --tb=short 2>&1
      2. Assert: all tests pass, no FAILED or ERROR
    Expected Result: 5+ integration tests pass
    Failure Indicators: Any FAILED or ERROR status
    Evidence: .sisyphus/evidence/task-12-integration.txt

  Scenario: Plugin chain type compatibility
    Tool: Bash (python3 -c)
    Preconditions: quant bundle works
    Steps:
      1. python3 -c "
         from scenarios.quant import build_quant_bundle
         from data_models import RunSession, Plan
         from memory_service.context_pack import ContextPack
         from core.loop.step_executor import LoopState
         b = build_quant_bundle()
         rs = RunSession(run_id='int-test', scenario='quant', config={})
         ctx = b.scenario_plugin.build_context(rs, {'task_summary': 'integration test'})
         proposal = b.proposal_engine.propose('mine factors', ContextPack(), [], Plan(plan_id='p', steps=[]), ctx)
         exp = b.experiment_generator.generate(proposal, rs, LoopState(iteration=0, max_iterations=1), [])
         artifact = b.coder.develop(exp, proposal, ctx)
         result = b.runner.run(artifact, ctx)
         feedback = b.feedback_analyzer.summarize(exp, result)
         print(f'Chain completed: ctx={type(ctx).__name__}, proposal={type(proposal).__name__}, exp={type(exp).__name__}, artifact={type(artifact).__name__}, result={type(result).__name__}, feedback={type(feedback).__name__}')
         print(f'Exit code: {result.exit_code}')
         print(f'Feedback decision: {feedback.decision}')
         "
      2. Assert: Chain completed with all correct type names, no exceptions
    Expected Result: All types chain together correctly
    Failure Indicators: TypeError, AttributeError, or wrong type names
    Evidence: .sisyphus/evidence/task-12-chain-types.txt
  ```

  **Commit**: YES (groups with T13)
  - Message: `test(quant): add integration test and verify no regression`
  - Files: `tests/test_quant_integration.py`
  - Pre-commit: `pytest tests/test_quant_integration.py -q`

- [ ] 13. Regression Test (ensure existing 638+ tests pass)

  **What to do**:
  - Run the full test suite to ensure no regression from quant additions:
    - `python3 -m pytest tests/ -q` → ALL existing tests still PASS
    - Verify total test count is ≥ 658 (638 existing + ≥20 new quant tests)
    - If any existing test fails, investigate and fix (likely import conflicts or registry changes)
  - Check specific risk areas:
    - `tests/test_task_02_plugin_contracts.py` — plugin contract tests still pass after registry change
    - `tests/test_integration_wiring.py` — runtime wiring still works
    - `tests/test_integration_full_loop.py` — full loop still works
    - Any test that imports from `plugins/__init__.py` — our modification didn't break anything

  **Must NOT do**:
  - ❌ Do NOT modify existing tests to make them pass — fix the source code instead
  - ❌ Do NOT skip/xfail existing tests
  - ❌ Do NOT change existing scenario plugins (data_science, synthetic_research)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Running tests and potentially fixing minor import issues
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 12)
  - **Blocks**: F1-F4
  - **Blocked By**: Task 11

  **References**:

  **Pattern References**:
  - `tests/` — entire test directory
  - `plugins/__init__.py` — the file we modified (Task 11) — most likely regression source

  **WHY Each Reference Matters**:
  - Our only modification to existing code is plugins/__init__.py — this is the highest-risk change for regression

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full regression suite
    Tool: Bash (python3 -m pytest)
    Preconditions: All quant code implemented
    Steps:
      1. python3 -m pytest tests/ -q 2>&1
      2. Assert: "X passed" where X ≥ 658, "0 failed"
    Expected Result: All tests pass, including new quant tests
    Failure Indicators: Any "failed" in output, total count < 658
    Evidence: .sisyphus/evidence/task-13-regression.txt

  Scenario: Specific high-risk tests
    Tool: Bash (python3 -m pytest)
    Preconditions: registry modified
    Steps:
      1. python3 -m pytest tests/test_task_02_plugin_contracts.py tests/test_integration_wiring.py -v --tb=short 2>&1
      2. Assert: all PASSED, no FAILED
    Expected Result: Plugin contract and wiring tests unaffected
    Failure Indicators: FAILED in output
    Evidence: .sisyphus/evidence/task-13-high-risk.txt
  ```

  **Commit**: YES (groups with T12)
  - Message: `test(quant): add integration test and verify no regression`
  - Files: (no new files — just verification)
  - Pre-commit: `pytest tests/ -q`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python3 -m pytest tests/ -q` (full suite). Review all new files in scenarios/quant/ for: `# type: ignore`, empty catches, print() in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA — Full Factor Mining Loop** — `unspecified-high`
  Start from clean state. Execute: `python3 -c "from scenarios.quant import build_quant_bundle; ..."` — instantiate bundle, call build_context, propose, generate, develop, run, summarize. Verify each step returns correct type. Verify metrics are computed. Verify feedback contains actionable information.
  Output: `Steps [N/N pass] | Metrics [computed/missing] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual code. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Commit | Tasks | Message | Pre-commit |
|--------|-------|---------|------------|
| 1 | T1, T2, T3 | `feat(quant): add mock data, constants, and prompt templates` | `pytest tests/test_quant_mock_data.py tests/test_quant_constants.py -q` |
| 2 | T4, T5 | `feat(quant): add metrics computation and code safety validator` | `pytest tests/test_quant_metrics.py tests/test_quant_code_safety.py -q` |
| 3 | T6 | `feat(quant): add lightweight backtest engine` | `pytest tests/test_quant_backtest.py -q` |
| 4 | T7, T8, T9, T10, T11 | `feat(quant): implement full plugin bundle (scenario, proposal, coder, runner, feedback)` | `pytest tests/test_quant_plugin.py -q` |
| 5 | T12, T13 | `test(quant): add integration test and verify no regression` | `pytest tests/ -q` |

---

## Success Criteria

### Verification Commands
```bash
# All quant tests pass
python3 -m pytest tests/test_quant_* -q  # Expected: ≥20 tests PASS

# No regression
python3 -m pytest tests/ -q  # Expected: ≥658 tests PASS (638 existing + ≥20 new)

# Plugin loads and creates bundle
python3 -c "from scenarios.quant import build_quant_bundle; b = build_quant_bundle(); print(b.scenario_name)"  # Expected: "quant"

# Full chain smoke test
python3 -c "
from scenarios.quant import build_quant_bundle
from data_models import RunSession
b = build_quant_bundle()
ctx = b.scenario_plugin.build_context(RunSession(run_id='test', scenario='quant', config={}), {})
print(f'Context: {ctx.scenario_name}, task: {ctx.task_summary[:50]}')
"  # Expected: no errors, prints context info
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All quant tests pass (≥20)
- [ ] All existing tests pass (≥638, no regression)
- [ ] Plugin registered and loadable
- [ ] Full factor mining chain executable
