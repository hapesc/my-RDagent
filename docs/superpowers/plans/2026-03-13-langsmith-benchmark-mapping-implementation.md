# LangSmith Benchmark Mapping Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current DeepEval-centered benchmark mainline with a LangSmith-centered benchmark stack in this repository's existing `app/` + `core/` runtime architecture, while using `MLE-bench` for `data_science` scoring and `QuantEval` for `quant` scoring.

**Architecture:** Introduce new top-level `benchmarking/` and `tracing/` packages as the authoritative benchmark and tracing feature paths. Keep runtime assembly in `app/runtime.py` and loop lifecycle control in `core/loop/run_service.py`, exposing explicit integration seams for tracing, benchmark payload extraction, and real-provider model metadata instead of creating a new `v2/` namespace.

**Tech Stack:** Python 3.11, LangSmith SDK, LangChain Core, `langchain-openai`, LiteLLM/OpenAI-compatible providers, pytest, Ruff, existing runtime/loop infrastructure, `MLE-bench`, `QuantEval`.

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `benchmarking/__init__.py` | Export benchmark package entrypoints |
| `benchmarking/contracts.py` | Benchmark task/config/evaluator protocols |
| `benchmarking/result_schema.py` | Normalized benchmark result dataclasses and failure buckets |
| `benchmarking/profiles.py` | `smoke` / `daily` / `full` profile definitions |
| `benchmarking/task_registry.py` | Materialize local, `MLE-bench`, and `QuantEval` tasks |
| `benchmarking/runner.py` | Benchmark orchestration against current runtime |
| `benchmarking/reporting.py` | JSON + Markdown benchmark summaries |
| `benchmarking/langsmith_backend.py` | LangSmith dataset/experiment/evaluator orchestration |
| `benchmarking/adapters/__init__.py` | Adapter exports |
| `benchmarking/adapters/mlebench_adapter.py` | `data_science` scenario-native scoring adapter |
| `benchmarking/adapters/quanteval_adapter.py` | `quant` scenario-native scoring adapter |
| `benchmarking/evaluators/__init__.py` | Evaluator exports |
| `benchmarking/evaluators/criteria.py` | Migrated criteria prompts from DeepEval assets |
| `benchmarking/evaluators/judge.py` | LangSmith-compatible judge evaluators |
| `benchmarking/evaluators/rules.py` | Pure Python structural evaluators |
| `tracing/__init__.py` | Tracing package exports |
| `tracing/config.py` | LangSmith tracing config and metadata helpers |
| `tracing/recorder.py` | Recorder protocol and node-boundary event hooks |
| `tracing/sinks.py` | LangSmith primary sink + JSONL mirror sink abstraction |
| `scripts/run_langsmith_benchmark.py` | Standalone benchmark CLI entrypoint |
| `tests/benchmarking/test_result_schema.py` | Result schema and contracts tests |
| `tests/benchmarking/test_profiles.py` | Profile tests |
| `tests/benchmarking/test_task_registry.py` | Task registry tests |
| `tests/benchmarking/test_runner.py` | Runner tests |
| `tests/benchmarking/test_langsmith_backend.py` | LangSmith backend tests |
| `tests/benchmarking/test_mlebench_adapter.py` | `MLE-bench` adapter tests |
| `tests/benchmarking/test_quanteval_adapter.py` | `QuantEval` adapter tests |
| `tests/benchmarking/test_criteria.py` | Criteria prompt tests |
| `tests/benchmarking/test_judge_evaluators.py` | Judge evaluator tests |
| `tests/benchmarking/test_rule_evaluators.py` | Structural rule tests |
| `tests/benchmarking/test_trace_sinks.py` | Trace sink tests |
| `tests/benchmarking/test_cli.py` | Benchmark CLI tests |
| `tests/test_benchmark_runtime_integration.py` | Focused runtime tracing integration tests if extending existing files becomes too noisy |
| `docs/superpowers/migrations/langsmith-benchmark-migration-matrix.md` | Migration ledger and dual-run policy |

### Modified files

| File | Change |
|------|--------|
| `pyproject.toml` | Add LangSmith and LangChain provider deps; keep legacy eval deps during migration |
| `tests/conftest.py` | Re-scope benchmark/eval gating away from `deepeval` |
| `app/runtime.py` | Inject tracing config and expose real-provider metadata |
| `llm/adapter.py` | Expose model metadata / LangChain-compatible hooks needed by runtime and judges |
| `core/loop/run_service.py` | Accept recorder hooks and expose benchmark-consumable result payloads |
| `trace_store/service.py` | Support JSONL mirror-sink role instead of primary benchmark dependency |
| `agentrd_cli.py` | Optional benchmark command registration if standalone script integration is desirable |
| `tests/test_runtime_wiring.py` | Cover tracing config and real-provider runtime wiring |
| `tests/test_task_10_run_service.py` | Cover recorder callbacks and payload extraction |
| `tests/test_cli.py` | Optional shared CLI helper coverage if benchmark script shares parsing utilities |
| `tests/evals/conftest.py` | Legacy-only gating updates |
| `tests/evals/test_p0_codegen.py` | Migrate to legacy regression or new benchmark interface smoke |
| `tests/evals/test_p1_costeer.py` | Migrate to legacy regression or new benchmark interface smoke |
| `tests/evals/test_p2_proposal.py` | Migrate to legacy regression or new benchmark interface smoke |
| `tests/evals/test_p3_report.py` | Migrate to legacy regression or new benchmark interface smoke |
| `tests/evals/test_p4_dataset_expansion.py` | Migrate to legacy regression or new benchmark interface smoke |

---

## Chunk 1: Core Benchmark Scaffolding

### Task 0: Add benchmark dependencies and benchmark-aware test gating

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/conftest.py`
- Create: `tests/benchmarking/test_result_schema.py`

- [ ] **Step 1: Write the failing test**

Add import-focused tests asserting:
- `langsmith` can be imported
- `langchain_openai` can be imported
- benchmark test collection no longer assumes `deepeval` is required

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_result_schema.py -v -k "dependency or gating"
python - <<'PY'
import importlib.util
assert importlib.util.find_spec("langsmith")
assert importlib.util.find_spec("langchain_openai")
PY
```
Expected: FAIL on current branch because the imports/tests are not wired yet.

- [ ] **Step 3: Write minimal implementation**

Modify `pyproject.toml`:
- add `langsmith` under benchmark/eval path
- add `langchain-openai`
- keep `deepeval` during migration

Modify `tests/conftest.py`:
- stop using `deepeval` import success as the collection gate for all eval-like tests
- treat `tests/evals/` as legacy-only gating
- allow new benchmark tests to collect without `deepeval`

- [ ] **Step 4: Run verification**

Run:
```bash
uv pip install -e ".[llm,eval,test]"
python - <<'PY'
import langsmith
import langchain_openai
print("deps ok")
PY
pytest tests/benchmarking/test_result_schema.py -v -k "dependency or gating"
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/conftest.py tests/benchmarking/test_result_schema.py
git commit -m "build(benchmark): add LangSmith deps and benchmark gating"
```

---

### Task 1: Define normalized benchmark result schema

**Files:**
- Create: `benchmarking/result_schema.py`
- Modify: `tests/benchmarking/test_result_schema.py`

- [ ] **Step 1: Write the failing test**

Add tests asserting:
- `FailureBucket` contains:
  - `infra_failure`
  - `generation_failure`
  - `artifact_missing`
  - `structural_failure`
  - `scenario_eval_failure`
  - `judge_failure`
  - `quality_failure`
  - `success`
- `BenchmarkCaseResult` contains:
  - `scenario`
  - `task_id`
  - `profile`
  - `agent_status`
  - `llm_provider`
  - `llm_model`
  - `judge_model`
  - `failure_bucket`
  - `scenario_score`
  - `scenario_metrics`
  - `judge_scores`
  - `timing`
  - `artifact_refs`
- `BenchmarkRunResult` supports stable dict serialization

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_result_schema.py -v -k "schema"
```
Expected: FAIL because `benchmarking/result_schema.py` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `benchmarking/result_schema.py` with dataclasses/enums only. Do not import LangSmith, `MLE-bench`, or `QuantEval`.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_result_schema.py -v -k "schema"
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/result_schema.py tests/benchmarking/test_result_schema.py
git commit -m "feat(benchmark): add normalized result schema"
```

---

### Task 2: Define benchmark contracts

**Files:**
- Create: `benchmarking/contracts.py`
- Modify: `tests/benchmarking/test_result_schema.py`

- [ ] **Step 1: Write the failing test**

Extend tests to expect:
- `BenchmarkTask`
- `BenchmarkRunConfig`
- `JudgeEvaluator`
- `ScenarioEvaluator`
- `TraceRecorder`

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_result_schema.py -v -k "contract"
```
Expected: FAIL because contracts are missing.

- [ ] **Step 3: Write minimal implementation**

Create `benchmarking/contracts.py` with dataclasses and protocols only. No runtime imports from LangSmith or external benchmark packages.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_result_schema.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/contracts.py tests/benchmarking/test_result_schema.py
git commit -m "refactor(benchmark): add benchmark contracts"
```

---

### Task 3: Add benchmark profiles

**Files:**
- Create: `benchmarking/profiles.py`
- Create: `tests/benchmarking/test_profiles.py`

- [ ] **Step 1: Write the failing test**

Add tests asserting:
- `smoke`, `daily`, `full` profiles exist
- `smoke` and `daily` do not require full external corpora by default
- each profile declares:
  - scenarios
  - enabled layers
  - rerun count
  - upload default

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_profiles.py -v
```
Expected: FAIL because `profiles.py` does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement `get_profile(name: str)` with fixed definitions. Preserve realistic loop budgets; reduce case count, not agent budget realism.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_profiles.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/profiles.py tests/benchmarking/test_profiles.py
git commit -m "feat(benchmark): add benchmark profiles"
```

---

## Chunk 2: Tracing and Runtime Integration

### Task 4: Add tracing config to runtime assembly

**Files:**
- Create: `tracing/config.py`
- Modify: `app/runtime.py`
- Modify: `tests/test_runtime_wiring.py`

- [ ] **Step 1: Write the failing test**

Add tests asserting `build_runtime()`:
- still works with tracing disabled
- exposes tracing config or `None`
- preserves existing runtime wiring and checkpoint store setup

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_runtime_wiring.py -v -k "tracing"
```
Expected: FAIL because tracing config is not part of runtime context.

- [ ] **Step 3: Write minimal implementation**

Create `tracing/config.py` with:
- env/config loader for LangSmith settings
- upload toggle
- metadata builder for benchmark project/suite tags

Modify `app/runtime.py`:
- add tracing config to `RuntimeContext`
- do not remove existing fields
- preserve existing coordinator/wiring behavior

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/test_runtime_wiring.py -v -k "tracing"
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tracing/config.py app/runtime.py tests/test_runtime_wiring.py
git commit -m "feat(runtime): add LangSmith tracing config"
```

---

### Task 5: Make real provider wiring benchmark-safe

**Files:**
- Modify: `app/runtime.py`
- Modify: `llm/adapter.py`
- Modify: `tests/test_runtime_wiring.py`

- [ ] **Step 1: Write the failing test**

Add tests asserting:
- mock path still works when explicitly configured
- real-provider config does not silently fall back to mock behavior
- configured provider/model identity is exposed for benchmark metadata

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_runtime_wiring.py -v -k "real provider or mock"
```
Expected: FAIL because runtime metadata and fallback behavior are insufficient for benchmark-critical use.

- [ ] **Step 3: Write minimal implementation**

Modify `app/runtime.py` and `llm/adapter.py` so benchmark paths can reliably discover the configured provider/model without scraping strings or silently dropping to mock behavior.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/test_runtime_wiring.py -v -k "real provider or mock"
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/runtime.py llm/adapter.py tests/test_runtime_wiring.py
git commit -m "feat(runtime): expose benchmark-safe provider metadata"
```

---

### Task 6: Add node-boundary recorder hooks to run service

**Files:**
- Create: `tracing/recorder.py`
- Modify: `core/loop/run_service.py`
- Modify: `tests/test_task_10_run_service.py`
- Modify or Create: `tests/test_benchmark_runtime_integration.py`

- [ ] **Step 1: Write the failing test**

Add tests expecting recorder callbacks with:
- `run_id`
- `scenario`
- `loop_iteration`
- `last_completed_node`
- `next_node`
- `checkpoint_id` when available

Also assert pause/resume ordering remains unchanged.

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_task_10_run_service.py -v -k "recorder"
```
Expected: FAIL because no recorder hook exists.

- [ ] **Step 3: Write minimal implementation**

Create recorder abstraction in `tracing/recorder.py`.

Modify `core/loop/run_service.py`:
- accept optional recorder dependency
- invoke recorder from the checkpoint boundary
- do not alter pause/fork/resume semantics

- [ ] **Step 4: Run unit verification**

Run:
```bash
pytest tests/test_task_10_run_service.py -v -k "recorder"
```
Expected: PASS

- [ ] **Step 5: Run integration verification**

Run:
```bash
pytest tests/test_benchmark_runtime_integration.py -v -k "resume or checkpoint"
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tracing/recorder.py core/loop/run_service.py tests/test_task_10_run_service.py tests/test_benchmark_runtime_integration.py
git commit -m "feat(runtime): record node-boundary trace metadata"
```

---

### Task 7: Expose benchmark-consumable run result payloads

**Files:**
- Modify: `core/loop/run_service.py`
- Modify: `tests/test_task_10_run_service.py`

- [ ] **Step 1: Write the failing test**

Add tests asserting completed/paused runs expose a stable payload containing:
- final state snapshot
- artifact/output references
- final status summary
- `llm_provider`
- `llm_model`
- `judge_model` when available

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_task_10_run_service.py -v -k "payload or final state"
```
Expected: FAIL because run service does not expose a dedicated benchmark payload.

- [ ] **Step 3: Write minimal implementation**

Add a retrieval method or explicit read model on run service. Do not require the benchmark runner to inspect private loop internals.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/test_task_10_run_service.py -v -k "payload or final state"
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/loop/run_service.py tests/test_task_10_run_service.py
git commit -m "feat(runtime): expose benchmark run result payloads"
```

---

### Task 8: Make JSONL trace storage a mirror sink

**Files:**
- Create: `tracing/sinks.py`
- Modify: `trace_store/service.py`
- Create: `tests/benchmarking/test_trace_sinks.py`

- [ ] **Step 1: Write the failing test**

Add tests asserting:
- LangSmith sink can be primary
- JSONL sink can mirror events
- benchmark reporting no longer reads JSONL directly

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_trace_sinks.py -v
```
Expected: FAIL because no sink abstraction exists.

- [ ] **Step 3: Write minimal implementation**

Create primary/mirror sink abstractions. Keep `trace_store/service.py` operational as local JSONL storage, but remove benchmark dependence on reading it directly.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_trace_sinks.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tracing/sinks.py trace_store/service.py tests/benchmarking/test_trace_sinks.py
git commit -m "refactor(tracing): make JSONL trace storage a mirror sink"
```

---

## Chunk 3: Benchmark Runner and Platform Layer

### Task 9: Add benchmark task registry

**Files:**
- Create: `benchmarking/task_registry.py`
- Create: `tests/benchmarking/test_task_registry.py`

- [ ] **Step 1: Write the failing test**

Add tests asserting the registry can materialize:
- `smoke`
- `daily`
- `full`

Each task record must contain at minimum:
- `scenario`
- `task_id`
- summary or source reference
- capability/failure tags where available
- source type (`local_fixture`, `mlebench`, `quanteval`, etc.)

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_task_registry.py -v
```
Expected: FAIL because registry does not exist.

- [ ] **Step 3: Write minimal implementation**

Use `tests/golden_tasks/*` as the local fixture source for `smoke`.
Expose adapter-backed task materialization for `MLE-bench` and `QuantEval` without requiring heavy corpora at import time.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_task_registry.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/task_registry.py tests/benchmarking/test_task_registry.py
git commit -m "feat(benchmark): add task registry"
```

---

### Task 10: Implement benchmark runner core and reporting

**Files:**
- Create: `benchmarking/runner.py`
- Create: `benchmarking/reporting.py`
- Create: `tests/benchmarking/test_runner.py`

- [ ] **Step 1: Write the failing test**

Add tests for a runner that:
- selects a profile
- materializes tasks
- executes the runtime target once per task
- reads run-service benchmark payloads
- applies rule evaluators
- applies scenario evaluator
- applies judge evaluators
- returns `BenchmarkRunResult`

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_runner.py -v
```
Expected: FAIL because runner/reporting do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement a synchronous runner first. Use fakes in tests. The runtime target must return structured outputs only and must not perform scenario-native grading itself.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_runner.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/runner.py benchmarking/reporting.py tests/benchmarking/test_runner.py
git commit -m "feat(benchmark): add runner core"
```

---

### Task 11: Add LangSmith backend

**Files:**
- Create: `benchmarking/langsmith_backend.py`
- Create: `tests/benchmarking/test_langsmith_backend.py`

- [ ] **Step 1: Write the failing test**

Add tests asserting a LangSmith backend can:
- create or bind a dataset
- launch an experiment
- attach case evaluators and summary evaluators
- return stable identifiers/handles

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_langsmith_backend.py -v
```
Expected: FAIL because backend does not exist.

- [ ] **Step 3: Write minimal implementation**

Make the LangSmith role explicit:
- benchmark target = current runtime execution
- case evaluators = rule + scenario + judge evaluators
- summary evaluators = experiment-level aggregation only

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_langsmith_backend.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/langsmith_backend.py tests/benchmarking/test_langsmith_backend.py
git commit -m "feat(benchmark): add LangSmith backend"
```

---

### Task 12: Add benchmark CLI entrypoint

**Files:**
- Create: `scripts/run_langsmith_benchmark.py`
- Create: `tests/benchmarking/test_cli.py`
- Optional Modify: `agentrd_cli.py`

- [ ] **Step 1: Write the failing test**

Add tests expecting CLI support for:
- `--profile`
- `--scenario`
- `--output-dir`
- `--compare-baseline`
- `--upload-results`

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_cli.py -v
```
Expected: FAIL because the CLI entrypoint is missing.

- [ ] **Step 3: Write minimal implementation**

Implement a standalone script first. Only touch `agentrd_cli.py` if shared parser behavior is required.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_cli.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/run_langsmith_benchmark.py tests/benchmarking/test_cli.py agentrd_cli.py
git commit -m "feat(benchmark): add benchmark CLI"
```

---

## Chunk 4: Scenario Adapters and Evaluators

### Task 13: Add `MLE-bench` adapter for `data_science`

**Files:**
- Create: `benchmarking/adapters/mlebench_adapter.py`
- Create: `tests/benchmarking/test_mlebench_adapter.py`

- [ ] **Step 1: Write the failing test**

Add tests that mock grading and expect:
- import succeeds without local corpora
- graded case maps into `BenchmarkCaseResult`
- missing assets raise a clear adapter-level error

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_mlebench_adapter.py -v
```
Expected: FAIL because adapter does not exist.

- [ ] **Step 3: Write minimal implementation**

Adapter contract:
- consumes `(inputs, outputs, reference_outputs)`-style task data
- reads `competition_id` from `reference_outputs`
- locates submission artifacts from runtime outputs
- returns scenario-native score without downloading corpora in unit tests

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_mlebench_adapter.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/adapters/mlebench_adapter.py tests/benchmarking/test_mlebench_adapter.py
git commit -m "feat(benchmark): add MLE-bench adapter"
```

---

### Task 14: Add QuantEval adapter for `quant`

**Files:**
- Create: `benchmarking/adapters/quanteval_adapter.py`
- Create: `tests/benchmarking/test_quanteval_adapter.py`

- [ ] **Step 1: Write the failing test**

Add tests expecting:
- normalized `BenchmarkCaseResult`
- sharpe / drawdown / returns in `scenario_metrics`
- invalid strategy failures classified clearly

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_quanteval_adapter.py -v
```
Expected: FAIL because adapter does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement CTA/backtest scoring only. Do not add unrelated benchmark modes.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_quanteval_adapter.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/adapters/quanteval_adapter.py tests/benchmarking/test_quanteval_adapter.py
git commit -m "feat(benchmark): add QuantEval adapter"
```

---

### Task 15: Extract criteria prompts from legacy DeepEval assets

**Files:**
- Create: `benchmarking/evaluators/criteria.py`
- Create: `tests/benchmarking/test_criteria.py`
- Reference: `evaluation_service/custom_metrics/proposal_quality.py`
- Reference: `evaluation_service/custom_metrics/costeer_efficiency.py`
- Reference: `evaluation_service/custom_metrics/report_quality.py`

- [ ] **Step 1: Write the failing test**

Add tests asserting criteria constants exist for:
- hypothesis specificity
- hypothesis feasibility
- feedback actionability
- report depth
- report coherence
- report faithfulness

Also assert faithfulness explicitly mentions bounded evidence or reference facts.

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_criteria.py -v
```
Expected: FAIL because criteria module does not exist.

- [ ] **Step 3: Write minimal implementation**

Copy prompt text out of legacy DeepEval assets. Rewrite only faithfulness wording where needed for stricter evidence grounding.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_criteria.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/evaluators/criteria.py tests/benchmarking/test_criteria.py
git commit -m "refactor(benchmark): extract evaluator criteria"
```

---

### Task 16: Implement judge evaluators

**Files:**
- Create: `benchmarking/evaluators/judge.py`
- Create: `tests/benchmarking/test_judge_evaluators.py`

- [ ] **Step 1: Write the failing test**

Add tests for judge evaluators that:
- accept `inputs`, `outputs`, `reference_outputs`
- return normalized score objects
- handle empty input safely

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_judge_evaluators.py -v
```
Expected: FAIL because judge evaluators do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement LangSmith-compatible BYO-LLM judge evaluators for the criteria extracted in Task 15. Do not import `deepeval`.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_judge_evaluators.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/evaluators/judge.py tests/benchmarking/test_judge_evaluators.py
git commit -m "feat(benchmark): add judge evaluators"
```

---

### Task 17: Implement structural rule evaluators

**Files:**
- Create: `benchmarking/evaluators/rules.py`
- Create: `tests/benchmarking/test_rule_evaluators.py`

- [ ] **Step 1: Write the failing test**

Add tests for:
- syntax validity
- import policy
- required function signatures
- required output keys/files

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/benchmarking/test_rule_evaluators.py -v
```
Expected: FAIL because rule evaluator module does not exist.

- [ ] **Step 3: Write minimal implementation**

Extract only pure Python rules. No LLM logic in this module.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/benchmarking/test_rule_evaluators.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarking/evaluators/rules.py tests/benchmarking/test_rule_evaluators.py
git commit -m "feat(benchmark): add structural rule evaluators"
```

---

### Task 18: Re-scope legacy `tests/evals/`

**Files:**
- Modify: `tests/evals/conftest.py`
- Modify: `tests/evals/test_p0_codegen.py`
- Modify: `tests/evals/test_p1_costeer.py`
- Modify: `tests/evals/test_p2_proposal.py`
- Modify: `tests/evals/test_p3_report.py`
- Modify: `tests/evals/test_p4_dataset_expansion.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write the failing test**

Add/update tests proving:
- `tests/evals/` are no longer the main benchmark runner
- DeepEval is not required by the new benchmark path
- legacy eval tests either target migrated interfaces or remain marked legacy regression

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/evals/ --collect-only -v --run-evals
```
Expected: FAIL or show legacy/mainline coupling that still needs removal.

- [ ] **Step 3: Write minimal implementation**

Update `tests/evals/` to either:
- regression tests for migrated evaluator logic, or
- smoke coverage of `benchmarking.runner`

Do not preserve DeepEval as a runtime dependency of the new benchmark stack.

- [ ] **Step 4: Run verification**

Run:
```bash
pytest tests/evals/ --collect-only -v --run-evals
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/evals/
git commit -m "test(eval): demote legacy eval suite"
```

---

## Chunk 5: Migration Ledger and Policy

### Task 19: Add migration ledger and dual-run policy

**Files:**
- Create: `docs/superpowers/migrations/langsmith-benchmark-migration-matrix.md`
- Modify: `docs/superpowers/plans/2026-03-13-langsmith-benchmark-mapping-implementation.md`

- [ ] **Step 1: Write the failing validation**

Write a validation expectation requiring each legacy benchmark asset to include:
- source file
- target file or replacement system
- status: `migrated` / `replaced` / `legacy-only` / `drop`
- retirement condition

- [ ] **Step 2: Run validation to verify it fails**

Run:
```bash
python - <<'PY'
from pathlib import Path
p = Path("docs/superpowers/migrations/langsmith-benchmark-migration-matrix.md")
assert p.exists(), "missing migration matrix"
PY
```
Expected: FAIL because the migration ledger does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create a migration ledger defining:
- `benchmarking/` as the only new benchmark feature path
- `evaluation_service/` legacy evaluators as asset sources only
- `tests/evals/` as legacy regression during overlap
- dual-run overlap policy
- retirement criteria for:
  - `evaluation_service/deepeval_bridge.py`
  - `evaluation_service/custom_metrics/*`
  - `tests/evals/*`
  - `pyproject.toml` `deepeval` dependency

- [ ] **Step 4: Run validation to verify it passes**

Run:
```bash
python - <<'PY'
from pathlib import Path
text = Path("docs/superpowers/migrations/langsmith-benchmark-migration-matrix.md").read_text(encoding="utf-8")
for needle in ["migrated", "replaced", "legacy-only", "drop", "tests/evals", "evaluation_service", "benchmarking/"]:
    assert needle in text, needle
print("migration ledger ok")
PY
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/migrations/langsmith-benchmark-migration-matrix.md docs/superpowers/plans/2026-03-13-langsmith-benchmark-mapping-implementation.md
git commit -m "docs(migration): add LangSmith benchmark migration ledger"
```

---

## Chunk 6: Full Verification

### Task 20: Run focused benchmark unit tests

- [ ] **Step 1: Run schema/profile/registry/backend/runner tests**

Run:
```bash
pytest tests/benchmarking/test_result_schema.py -v
pytest tests/benchmarking/test_profiles.py -v
pytest tests/benchmarking/test_task_registry.py -v
pytest tests/benchmarking/test_langsmith_backend.py -v
pytest tests/benchmarking/test_runner.py -v
```
Expected: PASS

- [ ] **Step 2: Run adapter tests**

Run:
```bash
pytest tests/benchmarking/test_mlebench_adapter.py -v
pytest tests/benchmarking/test_quanteval_adapter.py -v
```
Expected: PASS

- [ ] **Step 3: Run evaluator and sink tests**

Run:
```bash
pytest tests/benchmarking/test_criteria.py -v
pytest tests/benchmarking/test_judge_evaluators.py -v
pytest tests/benchmarking/test_rule_evaluators.py -v
pytest tests/benchmarking/test_trace_sinks.py -v
pytest tests/benchmarking/test_cli.py -v
```
Expected: PASS

---

### Task 21: Run runtime regression tests

- [ ] **Step 1: Run focused runtime tests**

Run:
```bash
pytest tests/test_runtime_wiring.py -v
pytest tests/test_task_10_run_service.py -v
```
Expected: PASS

- [ ] **Step 2: Run targeted lifecycle integration tests**

Run:
```bash
pytest tests/test_benchmark_runtime_integration.py -v
pytest tests/test_integration_full_loop.py -v
```
Expected: PASS

---

### Task 22: Run smoke benchmark profiles

- [ ] **Step 1: Run `data_science` smoke benchmark**

Run:
```bash
python scripts/run_langsmith_benchmark.py --profile smoke --scenario data_science --output-dir /tmp/langsmith-benchmark-ds
```
Expected: exits successfully and writes JSON + Markdown outputs.

- [ ] **Step 2: Run `quant` smoke benchmark**

Run:
```bash
python scripts/run_langsmith_benchmark.py --profile smoke --scenario quant --output-dir /tmp/langsmith-benchmark-quant
```
Expected: exits successfully and writes JSON + Markdown outputs.

- [ ] **Step 3: Verify output artifacts**

Run:
```bash
find /tmp/langsmith-benchmark-ds -maxdepth 2 -type f | sort
find /tmp/langsmith-benchmark-quant -maxdepth 2 -type f | sort
```
Expected: both contain at least one JSON result file and one Markdown summary file.

- [ ] **Step 4: Verify real-provider metadata**

Run:
```bash
python - <<'PY'
import json
from pathlib import Path

for root in [Path("/tmp/langsmith-benchmark-ds"), Path("/tmp/langsmith-benchmark-quant")]:
    json_files = sorted(root.rglob("*.json"))
    assert json_files, f"no json outputs in {root}"
    payload = json.loads(json_files[0].read_text(encoding="utf-8"))
    text = json.dumps(payload, ensure_ascii=False).lower()
    assert "mock" not in text, f"mock path detected in {json_files[0]}"
    assert any(key in text for key in ["provider", "llm_model", "llm_provider", "judge_model"]), json_files[0]
print("real provider metadata verified")
PY
```
Expected: PASS

---

### Task 23: Verify DeepEval is off the benchmark mainline

- [ ] **Step 1: Search benchmark-critical paths for DeepEval**

Run:
```bash
rg -n "deepeval" benchmarking tracing scripts/run_langsmith_benchmark.py tests/benchmarking
```
Expected: zero matches.

- [ ] **Step 2: Verify legacy evals are explicitly legacy-only**

Run:
```bash
rg -n "deepeval" tests/evals evaluation_service
```
Expected: zero matches or matches recorded as `legacy-only` in `docs/superpowers/migrations/langsmith-benchmark-migration-matrix.md`.

- [ ] **Step 3: Run broader regression suite**

Run:
```bash
pytest tests/benchmarking -v
pytest tests/ -v --ignore=tests/evals --ignore=tests/benchmarking
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-03-13-langsmith-benchmark-mapping-implementation.md
git commit -m "docs(plan): add mapped LangSmith benchmark implementation plan"
```

---

Plan complete and saved to `docs/superpowers/plans/2026-03-13-langsmith-benchmark-mapping-implementation.md`. Ready to execute?
