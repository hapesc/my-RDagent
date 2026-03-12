# Agentic R&D Platform

An open-source implementation of the [R&D-Agent](https://arxiv.org/abs/2404.11276) workflow for iterative research, code generation, execution, and evaluation.

The platform runs an autonomous loop:

`propose -> code -> execute -> evaluate -> repeat`



## Built-In Scenarios

- `data_science`: directly runnable from the default runtime
- `synthetic_research`: directly runnable from the default runtime
- `quant`: registered in the plugin registry, but the default `build_runtime()` path does not inject a market-data provider; use custom wiring or `scripts/run_quant_e2e.py`

## Prerequisites

- Python `3.11+`
- [uv](https://docs.astral.sh/uv/) recommended
- A real LLM provider configuration for actual runs
- Docker for sandboxed execution, or `AGENTRD_ALLOW_LOCAL_EXECUTION=1` for local execution

Important runtime constraint:

- `app.startup` can validate config without an LLM provider
- `agentrd_cli.py`, `app.runtime.build_runtime()`, and the FastAPI control plane require `RD_AGENT_LLM_PROVIDER=litellm`
- Runtime mock providers still exist in tests, but there is no mock fallback for normal runs

## Install

Typical developer install:

```bash
git clone https://github.com/hapesc/my-RDagent.git
cd my-RDagent

uv venv
uv pip install -e ".[all]"
```

Available shortcuts:

```bash
make install      # core package only; not enough for real LLM runs
make install-all  # installs all optional deps
```

## Validate Config

`app.startup` only loads config and prints the effective JSON:

```bash
cp config.example.yaml config.yaml
python -m app.startup
python -m app.startup --config ./config.yaml
```

## Configure the Runtime

Minimum environment for real runs:

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=openai/gpt-4o-mini
export RD_AGENT_LLM_API_KEY=your-api-key
export AGENTRD_ALLOW_LOCAL_EXECUTION=1
```

Notes:

- `AGENTRD_ALLOW_LOCAL_EXECUTION=1` is only needed when Docker is unavailable and the selected scenario executes code locally
- when a real provider is enabled, unspecified defaults are narrowed to a conservative guardrail profile during runtime assembly
- for `litellm`, there are two supported runtime modes:
  - API key mode: keep `RD_AGENT_LLM_API_KEY` set and use your normal provider/model path
  - ChatGPT auth mode: leave `RD_AGENT_LLM_API_KEY` empty and set `RD_AGENT_LLM_MODEL` to `chatgpt/...` or a bare `gpt-*` model such as `gpt-5`
- bare `gpt-*` models are routed through LiteLLM ChatGPT auth only when `RD_AGENT_LLM_API_KEY` is empty
- exact config fields are documented in [`dev_doc/configuration.md`](dev_doc/configuration.md)

## Run a Simple Experiment

The only supported run entrypoint is:

```bash
rdagent run --config ./config.yaml ...
```

Equivalent source invocation:

```bash
python agentrd_cli.py run --config ./config.yaml ...
```

Recommended `config.yaml` structure for stable run settings:

```yaml
run_defaults:
  scenario: data_science
  stop_conditions:
    max_loops: 1
    max_duration_sec: 300
  step_overrides:
    running:
      timeout_sec: 120
  entry_input:
    id_column: id
    label_column: label
```

For `data_science` runs that need a local dataset file, keep stable defaults in `config.yaml` and override only high-frequency fields from CLI:

```bash
rdagent run \
  --config ./config.yaml \
  --task-summary "classify iris from local csv" \
  --data-source /absolute/path/to/train.csv
```

Legacy advanced path remains available:

```bash
rdagent run \
  --config ./config.yaml \
  --scenario data_science \
  --input '{
    "task_summary":"classify iris from local csv",
    "entry_input":{"data_source":"/absolute/path/to/train.csv"},
    "max_loops":1
  }'
```

`data_science` also understands optional split-related fields in the same payload:

- `id_column`
- `label_column`
- `train_ratio`
- `test_ratio`
- `split_seed` or `seed`

Current execution caveat:

- the default Docker execution backend mounts only the generated workspace, not an arbitrary host data path
- a host file path in `data_source` therefore works reliably only when the run actually executes locally, or when you provide your own runtime/backend wiring
- supported file formats for split-manifest inference are `.csv`, `.jsonl`, and `.ndjson`

Recommended `synthetic_research` path:

```bash
rdagent run \
  --config ./config.yaml \
  --scenario synthetic_research \
  --task-summary "write a short brief about evaluation benchmark failure modes"
```

If you want to seed the run with explicit topics:

```bash
rdagent run \
  --config ./config.yaml \
  --scenario synthetic_research \
  --input '{
    "task_summary":"write a short brief about evaluation benchmark failure modes",
    "reference_topics":["evaluation", "benchmarking", "failure analysis"],
    "max_loops":1
  }'
```

`synthetic_research` is the easiest built-in scenario for first-time validation because it does not depend on a dataset path or code-execution sandbox.

Recommended `quant` path with a local OHLCV CSV:

```bash
rdagent run \
  --config ./config.yaml \
  --scenario quant \
  --task-summary "mine a momentum factor from local OHLCV data" \
  --data-source /absolute/path/to/ohlcv.csv
```

The local quant CSV format is fixed and must contain exactly these columns:

```text
date,stock_id,open,high,low,close,volume
```

Example:

```csv
date,stock_id,open,high,low,close,volume
2021-07-01,AAPL,136.60,137.33,135.76,136.96,52485800
2021-07-01,MSFT,271.60,272.00,269.60,271.40,17887700
```

Notes for `quant`:

- only local CSV input is supported through the default CLI path
- the file must provide OHLCV rows, one `(date, stock_id)` observation per line
- the runtime still requires a real LLM provider, but it now auto-builds a file-based quant data provider when `--data-source` is present
- `python scripts/run_quant_e2e.py` remains useful when you want a yfinance-based wrapper that fetches OHLCV first and then delegates to the same unified CLI path

The script now acts as a wrapper over `agentrd run`, not a second runtime entrypoint. It accepts:

- `--tickers`
- `--start-date`
- `--end-date`
- `--task-summary`
- `--max-loops`

Use `quant` when you want alpha-factor mining over OHLCV data; use `data_science` for general local dataset experiments and `synthetic_research` for brief/report generation.

Inspect traces:

```bash
rdagent trace --run-id <RUN_ID> --format table
rdagent health-check --verbose
```

## Start the Control Plane

```bash
uvicorn app.api_main:app --host 127.0.0.1 --port 8000
streamlit run ui/trace_ui.py
```

API endpoints exposed by the control plane:

| Method | Endpoint |
|--------|----------|
| `POST` | `/runs` |
| `GET` | `/runs/{run_id}` |
| `POST` | `/runs/{run_id}/pause` |
| `POST` | `/runs/{run_id}/resume` |
| `POST` | `/runs/{run_id}/stop` |
| `GET` | `/runs/{run_id}/events` |
| `GET` | `/runs/{run_id}/artifacts` |
| `GET` | `/runs/{run_id}/branches` |
| `GET` | `/scenarios` |
| `GET` | `/health` |

## Configuration Summary

Configuration precedence:

1. Built-in defaults
2. `config.yaml`
3. Environment variables

Two details matter in practice:

- `app.config.load_config()` still defaults `llm_provider` to `mock` for backward-compatible parsing
- the executable runtime rejects that default and requires `RD_AGENT_LLM_PROVIDER=litellm`

Common fields:

| Variable | Default in `AppConfig` | Purpose |
|----------|------------------------|---------|
| `AGENTRD_ARTIFACT_ROOT` | `/tmp/rd_agent_artifacts` | Artifacts and checkpoints |
| `AGENTRD_WORKSPACE_ROOT` | `/tmp/rd_agent_workspace` | Per-run workspaces |
| `AGENTRD_SQLITE_PATH` | `/tmp/rd_agent.sqlite3` | Metadata store |
| `AGENTRD_TRACE_STORAGE_PATH` | `/tmp/rd_agent_trace/events.jsonl` | Trace event path |
| `AGENTRD_ALLOW_LOCAL_EXECUTION` | `false` | Local execution fallback when Docker is unavailable |
| `RD_AGENT_LLM_PROVIDER` | `mock` in config loader | Must be `litellm` for real runtime entrypoints |
| `RD_AGENT_LLM_MODEL` | `gpt-4o-mini` | Default model identifier |
| `RD_AGENT_COSTEER_MAX_ROUNDS` | `1` | CoSTEER round cap before real-provider guardrails are applied |

`run_defaults` in `config.yaml` is merged into `rdagent run` before CLI flags and `--input` overrides are applied.

## Testing

```bash
pytest tests/ -v
./scripts/run_task17_acceptance.sh
./scripts/run_task23_acceptance.sh
```

Real-provider end-to-end scripts:

```bash
python scripts/run_data_science_e2e.py
python scripts/run_synthetic_research_e2e.py
python scripts/run_quant_e2e.py
```

The quant E2E path uses custom runtime wiring and a real data provider; it is not the same as the default CLI runtime.

## Repository Layout

```text
app/                    runtime assembly, config, control plane
core/                   loop engine, execution, storage, reasoning
exploration_manager/    scheduler, pruning, trace merging
evaluation_service/     scoring and selection
llm/                    adapters, prompts, structured schemas
memory_service/         memory lookup and optional hypothesis storage
plugins/                plugin registry and contracts
scenarios/              built-in scenario implementations
ui/                     streamlit trace UI
tests/                  unit, integration, and acceptance coverage
dev_doc/                architecture, operations, ADRs
```

## Documentation

| Document | Description |
|----------|-------------|
| [`QUICKSTART.md`](QUICKSTART.md) | Practical setup guide for local and Docker workflows |
| [`dev_doc/configuration.md`](dev_doc/configuration.md) | Full config and env mapping |
| [`dev_doc/runbook.md`](dev_doc/runbook.md) | Operations runbook |
| [`dev_doc/deployment.md`](dev_doc/deployment.md) | Single-host deployment guide |
| [`dev_doc/api_reference.md`](dev_doc/api_reference.md) | Control-plane request and response contracts |
| [`dev_doc/architecture.md`](dev_doc/architecture.md) | System architecture and implementation reality |


## License

[MIT](LICENSE)
