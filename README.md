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
- `cli.py`, `agentrd_cli.py`, `app.runtime.build_runtime()`, and the FastAPI control plane require `RD_AGENT_LLM_PROVIDER=litellm`
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
- exact config fields are documented in [`dev_doc/configuration.md`](dev_doc/configuration.md)

## Run a Simple Experiment

Quick CLI:

```bash
python cli.py \
  --config ./config.yaml \
  --scenario data_science \
  --task "classify iris dataset" \
  --max-steps 1
```

Full JSON-oriented CLI:

```bash
python agentrd_cli.py run \
  --config ./config.yaml \
  --scenario synthetic_research \
  --loops-per-call 1 \
  --max-loops 1 \
  --input '{"task_summary":"summarize recent trends in evaluation benchmarks","max_loops":1}'
```

Inspect traces:

```bash
python agentrd_cli.py trace --run-id <RUN_ID> --format table
python agentrd_cli.py health-check --verbose
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
| `RD_AGENT_COSTEER_MAX_ROUNDS` | `3` | CoSTEER round cap before real-provider guardrails are applied |

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
