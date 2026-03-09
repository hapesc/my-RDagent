# Agentic R&D Platform

An open-source implementation of the [R&D-Agent](https://arxiv.org/abs/2404.11276) framework — an LLM-agent system that automates iterative data science and machine learning engineering workflows.

Instead of running experiments manually, you describe a task and the platform runs an autonomous loop: **propose → code → execute → evaluate → repeat**, improving with each iteration.

## What It Does

The platform implements the R&D-Agent paper's six framework components:

| Component | Status | Description |
|-----------|--------|-------------|
| FC-2 Exploration Path | Implemented | MCTS-based tree search over experiment branches with pruning and trace merging |
| FC-3 Reasoning Pipeline | Implemented | 4-stage scientific reasoning (Analyze → Identify → Hypothesize → Design) with virtual evaluation |
| FC-1 Planning | Partial | Static planning; dynamic time-aware budget allocation not yet implemented |
| FC-4 Memory Context | Partial | Basic memory service; embedding-based retrieval and cross-branch knowledge sharing pending |
| FC-5 Coding Workflow | Partial | Single-round coding; multi-round CoSTEER evolution in progress |
| FC-6 Evaluation Strategy | Partial | Basic scoring; automated data splitting and multi-candidate ranking pending |

See [`dev_doc/paper_gap_analysis.md`](dev_doc/paper_gap_analysis.md) for a detailed comparison with the paper.

## Architecture

```
User ──→ CLI / REST API ──→ Run Orchestrator ──→ Scenario Plugin
              │                    │                    │
              │                    ├── Loop Engine       ├── Proposal Engine
              │                    ├── Step Executor     ├── Experiment Generator
              │                    ├── Branch Manager    ├── Coder
              │                    └── Resume Manager    ├── Runner
              │                                         └── Feedback Analyzer
              │
         Trace UI ──→ SQLite + Trace Store + Artifact Store
```

The system is plugin-based. The loop engine is generic — scenario-specific logic lives in plugins. Three scenarios ship out of the box:

- **`data_science`** — generates and executes small data science experiments
- **`synthetic_research`** — generates lightweight research briefs and findings
- **`quant`** — automated alpha factor mining: LLM proposes factors → backtest evaluates → feedback improves (uses real market data via yfinance)

## Quick Start

### Prerequisites

- Python 3.9+
- (Optional) Docker for sandboxed code execution
- An LLM API key (e.g. `GEMINI_API_KEY`) — **required for real runs**. There is no mock fallback at runtime; missing LLM config will raise an error.
- (Optional) `yfinance` for the quant scenario's real market data

### 1. Verify Configuration

```bash
python3 -m app.startup

# or validate with a specific config file
python3 -m app.startup --config ./config.yaml
```

This prints the active configuration as JSON. All settings have sensible defaults — no setup required for a local trial.

### 2. Run an Experiment

```bash
# Simple CLI
python3 cli.py --config ./config.yaml --scenario data_science --task "classify iris dataset" --max-steps 3

# Dry run (validate config only, no execution)
python3 cli.py --dry-run --task "verify setup"
```

Or use the full CLI with JSON input:

```bash
export AGENTRD_ALLOW_LOCAL_EXECUTION=1

python3 agentrd_cli.py run \
  --config ./config.yaml \
  --scenario data_science \
  --loops-per-call 1 \
  --max-loops 3 \
  --input '{"task_summary": "classify iris dataset", "max_loops": 3}'
```

### 3. Query Traces

```bash
python3 agentrd_cli.py trace --run-id <RUN_ID> --format table
```

### 4. Start the Control Plane & UI (Optional)

Requires `fastapi`, `uvicorn`, and `streamlit`:

```bash
pip install fastapi uvicorn streamlit

# REST API
uvicorn app.api_main:app --host 127.0.0.1 --port 8000

# Trace UI (in a separate terminal)
streamlit run ui/trace_ui.py
```

### 5. Health Check

```bash
python3 agentrd_cli.py health-check --verbose
```

## Configuration

Configuration precedence is:

1. Built-in defaults
2. Optional YAML config file (`./config.yaml` by default)
3. Environment variables (highest priority)

**Note**: Empty-string environment variables (e.g., `export RD_AGENT_LLM_API_KEY=""`) are treated as unset and will not override YAML or default values.

To start from a template:

```bash
cp config.example.yaml config.yaml
```

Use `--config <path>` in `app.startup`, `cli.py`, and `agentrd_cli.py` to load a non-default YAML file.

### App / Runtime (`AGENTRD_*`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AGENTRD_ENV` | string | `dev` | Runtime environment |
| `AGENTRD_DEFAULT_SCENARIO` | string | `data_science` | Default scenario plugin |
| `AGENTRD_ARTIFACT_ROOT` | path | `/tmp/rd_agent_artifacts` | Storage root for run artifacts |
| `AGENTRD_WORKSPACE_ROOT` | path | `/tmp/rd_agent_workspace` | Workspace for intermediate state |
| `AGENTRD_TRACE_STORAGE_PATH` | path | `/tmp/rd_agent_trace/events.jsonl` | Trace event log path |
| `AGENTRD_SQLITE_PATH` | path | `/tmp/rd_agent.sqlite3` | SQLite metadata database |
| `AGENTRD_SANDBOX_TIMEOUT_SEC` | int | `300` | Execution sandbox timeout (seconds) |
| `AGENTRD_ALLOW_LOCAL_EXECUTION` | bool | `false` | Allow local Python execution (when Docker is unavailable) |
| `AGENTRD_LOG_LEVEL` | string | `INFO` | Log verbosity |

### Model / Loop Behavior (`RD_AGENT_*`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RD_AGENT_LLM_PROVIDER` | string | — | LLM backend (`litellm`, `openai`). **Required** — no mock fallback. |
| `RD_AGENT_LLM_API_KEY` | string | — | API key for LLM provider |
| `RD_AGENT_LLM_MODEL` | string | `gpt-4o-mini` | Model identifier |
| `RD_AGENT_LLM_BASE_URL` | string | — | Custom LLM endpoint URL |
| `RD_AGENT_COSTEER_MAX_ROUNDS` | int | `1` | Max reasoning rounds per step |
| `RD_AGENT_MCTS_WEIGHT` | float | `1.41` | MCTS exploration weight (UCB coefficient) |
| `RD_AGENT_MCTS_C_PUCT` | float | `1.41` | MCTS PUCT coefficient |
| `RD_AGENT_LAYER0_N_CANDIDATES` | int | `5` | Layer-0 diverse root candidates |
| `RD_AGENT_LAYER0_K_FORWARD` | int | `2` | Layer-0 roots to forward |
| `RD_AGENT_PRUNE_THRESHOLD` | float | `0.5` | Branch pruning score threshold |

## Per-Step Overrides

Each run can override model and timeout settings per step (`proposal`, `coding`, `running`, `feedback`):

```bash
python3 agentrd_cli.py run \
  --scenario data_science \
  --input '{
    "task_summary": "override demo",
    "max_loops": 1,
    "step_overrides": {
      "proposal": {"model": "gpt-4o"},
      "coding": {"model": "gpt-4o-mini"},
      "running": {"timeout_sec": 30},
      "feedback": {"model": "gpt-4o"}
    }
  }'
```

To audit the effective config for a run:

```bash
python3 agentrd_cli.py trace --run-id <RUN_ID> --format json
```

The `run.config_snapshot.step_overrides` field shows the final merged config; `requested_step_overrides` shows what was requested.

## REST API

When running the FastAPI control plane:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/runs` | Create and start a new run |
| `GET` | `/runs/{run_id}` | Get run summary |
| `POST` | `/runs/{run_id}/pause` | Pause a running experiment |
| `POST` | `/runs/{run_id}/resume` | Resume a paused experiment |
| `POST` | `/runs/{run_id}/stop` | Stop a running experiment |
| `GET` | `/runs/{run_id}/events` | List trace events (paginated) |
| `GET` | `/runs/{run_id}/artifacts` | List run artifacts |
| `GET` | `/runs/{run_id}/branches` | List experiment branches |
| `GET` | `/scenarios` | List available scenario plugins |
| `GET` | `/health` | System health check |

## Testing

```bash
# Full regression suite (739 tests)
python3 -m pytest tests -q

# Acceptance tests
./scripts/run_task17_acceptance.sh
```

### End-to-End Tests (Real LLM)

These scripts run a full loop-engine cycle with a real LLM backend (Gemini). They require `GEMINI_API_KEY` to be set.

```bash
# Quant scenario — real yfinance data + LLM factor generation + backtest
python3 scripts/run_quant_e2e.py

# Data Science scenario — real LLM reasoning + coding + local execution
python3 scripts/run_data_science_e2e.py

# Synthetic Research scenario — real LLM research brief + findings
python3 scripts/run_synthetic_research_e2e.py
```

## Project Structure

```
├── app/                    # Runtime assembly, config, API, control plane
├── core/
│   ├── loop/               # Loop engine, step executor, resume manager
│   ├── reasoning/          # Scientific reasoning pipeline, virtual evaluator
│   ├── execution/          # Workspace manager, sandbox backends
│   └── storage/            # SQLite store, branch trace store, checkpoints
├── exploration_manager/    # MCTS scheduler, branch pruning, trace merging
├── llm/                    # LLM adapter, structured output schemas
├── memory_service/         # Historical context and knowledge retrieval
├── evaluation_service/     # Code and result evaluation
├── planner/                # Plan generation for each iteration
├── plugins/                # Plugin registry and scenario contracts
├── scenarios/
│   ├── data_science/       # Data science scenario plugin
│   ├── synthetic_research/ # Synthetic research scenario plugin
│   └── quant/              # Quant factor mining scenario (yfinance + backtest)
├── ui/                     # Streamlit trace viewer
├── tests/                  # Test suite covering all layers
└── dev_doc/                # Architecture docs, gap analysis, ADRs
```

## Documentation

| Document | Description |
|----------|-------------|
| [`dev_doc/quant_scenario.md`](dev_doc/quant_scenario.md) | Quant scenario architecture and usage |
| [`dev_doc/architecture.md`](dev_doc/architecture.md) | Full system architecture with Mermaid diagrams |
| [`dev_doc/paper_gap_analysis.md`](dev_doc/paper_gap_analysis.md) | Detailed comparison with the R&D-Agent paper |
| [`dev_doc/configuration.md`](dev_doc/configuration.md) | Complete environment variable reference |
| [`dev_doc/runbook.md`](dev_doc/runbook.md) | Operations runbook |
| [`dev_doc/deployment.md`](dev_doc/deployment.md) | Minimal deployment guide |
| [`dev_doc/api_reference.md`](dev_doc/api_reference.md) | REST API reference and contracts |
| [`dev_doc/product_requirements.md`](dev_doc/product_requirements.md) | Core product requirements |
| [`dev_doc/system_specifications.md`](dev_doc/system_specifications.md) | Detailed system specifications |

## Acknowledgments

This project is an independent implementation inspired by the [R&D-Agent paper](https://arxiv.org/abs/2404.11276) by Xu Yang, Xiao Yang, Shikai Fang et al. from Microsoft Research.

## License

This project is for research and educational purposes.
