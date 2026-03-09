# Config and Env Mapping

## Load Order

Configuration is resolved in this order:

1. Built-in defaults
2. YAML file (`config.yaml` at project root, or `--config <path>`)
3. Environment variables (highest priority)

Empty-string environment variables (e.g., `export RD_AGENT_LLM_API_KEY=""`) are ignored and treated as unset. This ensures they do not accidentally override YAML or default values.

This keeps env-only usage backward compatible while enabling file-based baseline config.

## Flat YAML Schema

`config.yaml` uses a flat key schema matching `AppConfig` fields directly.

Example:

```yaml
env: dev
default_scenario: data_science
llm_provider: mock
```

## Field Mapping

| YAML Key | Env Var | Type | Default |
|---|---|---|---|
| `env` | `AGENTRD_ENV` | string | `dev` |
| `default_scenario` | `AGENTRD_DEFAULT_SCENARIO` | string | `data_science` |
| `artifact_root` | `AGENTRD_ARTIFACT_ROOT` | path | `/tmp/rd_agent_artifacts` |
| `workspace_root` | `AGENTRD_WORKSPACE_ROOT` | path | `/tmp/rd_agent_workspace` |
| `trace_storage_path` | `AGENTRD_TRACE_STORAGE_PATH` | path | `/tmp/rd_agent_trace/events.jsonl` |
| `sqlite_path` | `AGENTRD_SQLITE_PATH` | path | `/tmp/rd_agent.sqlite3` |
| `sandbox_timeout_sec` | `AGENTRD_SANDBOX_TIMEOUT_SEC` | int | `300` |
| `allow_local_execution` | `AGENTRD_ALLOW_LOCAL_EXECUTION` | bool | `false` |
| `log_level` | `AGENTRD_LOG_LEVEL` | string | `INFO` |
| `llm_provider` | `RD_AGENT_LLM_PROVIDER` | string | `mock` |
| `llm_api_key` | `RD_AGENT_LLM_API_KEY` | string/null | `null` |
| `llm_model` | `RD_AGENT_LLM_MODEL` | string | `gpt-4o-mini` |
| `llm_base_url` | `RD_AGENT_LLM_BASE_URL` | string/null | `null` |
| `costeer_max_rounds` | `RD_AGENT_COSTEER_MAX_ROUNDS` | int | `1` |
| `mcts_exploration_weight` | `RD_AGENT_MCTS_WEIGHT` | float | `1.41` |
| `mcts_c_puct` | `RD_AGENT_MCTS_C_PUCT` | float | `1.41` |
| `mcts_reward_mode` | `RD_AGENT_MCTS_REWARD_MODE` | string | `score_based` |
| `layer0_n_candidates` | `RD_AGENT_LAYER0_N_CANDIDATES` | int | `5` |
| `layer0_k_forward` | `RD_AGENT_LAYER0_K_FORWARD` | int | `2` |
| `prune_threshold` | `RD_AGENT_PRUNE_THRESHOLD` | float | `0.5` |
| `debug_mode` | `RD_AGENT_DEBUG_MODE` | bool | `false` |
| `debug_sample_fraction` | `RD_AGENT_DEBUG_SAMPLE_FRACTION` | float | `0.1` |
| `debug_max_epochs` | `RD_AGENT_DEBUG_MAX_EPOCHS` | int | `5` |
| `enable_hypothesis_storage` | `RD_AGENT_HYPOTHESIS_STORAGE` | bool | `false` |
| `use_llm_planning` | `RD_AGENT_LLM_PLANNING` | bool | `false` |

## Startup Validation

```bash
python3 -m app.startup
python3 -m app.startup --config ./config.yaml
```
