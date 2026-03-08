# Config Env Mapping

## Prefix Roles

- **`AGENTRD_*`**: App/runtime settings (paths, execution modes, observability)
- **`RD_AGENT_*`**: Model, loop, and reasoning behavior settings

## App/Runtime Settings (`AGENTRD_*`)

| Env Var | Type | Default | Description |
|---|---|---|---|
| `AGENTRD_ENV` | string | `dev` | Runtime environment (e.g., `dev`, `prod`) |
| `AGENTRD_DEFAULT_SCENARIO` | string | `data_science` | Default scenario plugin to load on startup |
| `AGENTRD_ARTIFACT_ROOT` | path | `/tmp/rd_agent_artifacts` | Storage root for run artifacts and outputs |
| `AGENTRD_WORKSPACE_ROOT` | path | `/tmp/rd_agent_workspace` | Workspace root for intermediate execution state |
| `AGENTRD_TRACE_STORAGE_PATH` | path | `/tmp/rd_agent_trace/events.jsonl` | Path to trace event JSONL log |
| `AGENTRD_SQLITE_PATH` | path | `/tmp/rd_agent.sqlite3` | Path to SQLite metadata database |
| `AGENTRD_SANDBOX_TIMEOUT_SEC` | int | `300` | Execution sandbox timeout in seconds |
| `AGENTRD_ALLOW_LOCAL_EXECUTION` | bool | `false` | Explicit opt-in for local Python execution (when Docker unavailable) |
| `AGENTRD_LOG_LEVEL` | string | `INFO` | Log verbosity (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Model and Loop Behavior (`RD_AGENT_*`)

| Env Var | Type | Default | Description |
|---|---|---|---|
| `RD_AGENT_LLM_PROVIDER` | string | `mock` | LLM provider backend (e.g., `mock`, `litellm`, `openai`) |
| `RD_AGENT_LLM_API_KEY` | string | (none) | API key for LLM provider authentication |
| `RD_AGENT_LLM_MODEL` | string | `gpt-4o-mini` | Model identifier for LLM calls |
| `RD_AGENT_LLM_BASE_URL` | string | (none) | Custom base URL for LLM provider (e.g., local proxy) |
| `RD_AGENT_COSTEER_MAX_ROUNDS` | int | `1` | Max reasoning rounds in costeer (1=single, 3+=multi-round) |
| `RD_AGENT_MCTS_WEIGHT` | float | `1.41` | MCTS exploration weight (UCB formula coefficient) |
| `RD_AGENT_MCTS_C_PUCT` | float | `1.41` | MCTS C_PUCT coefficient (balance exploitation vs exploration) |
| `RD_AGENT_MCTS_REWARD_MODE` | string | `score_based` | MCTS reward aggregation mode (e.g., `score_based`) |
| `RD_AGENT_LAYER0_N_CANDIDATES` | int | `5` | Layer-0 diverse root generation: number of candidate roots |
| `RD_AGENT_LAYER0_K_FORWARD` | int | `2` | Layer-0 diverse root generation: number of roots to forward |
| `RD_AGENT_PRUNE_THRESHOLD` | float | `0.5` | Node pruning threshold (remove nodes with score below this) |
| `RD_AGENT_DEBUG_MODE` | bool | `false` | Enable debug mode with structured logging and sampling |
| `RD_AGENT_DEBUG_SAMPLE_FRACTION` | float | `0.1` | Fraction of steps to log in debug mode (0.0–1.0) |
| `RD_AGENT_DEBUG_MAX_EPOCHS` | int | `5` | Max epochs for debug sampling |
| `RD_AGENT_HYPOTHESIS_STORAGE` | bool | `false` | Enable hypothesis storage (experimental) |
| `RD_AGENT_LLM_PLANNING` | bool | `false` | Enable LLM-based planning mode (experimental) |

## Startup Validation Command

```bash
python3 -m app.startup
```

输出为当前生效配置 JSON。
