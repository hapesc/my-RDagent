# Config and Env Mapping

## Resolution Order

`app.config.load_config()` 按以下顺序解析配置：

1. 内置默认值
2. YAML 文件，默认是项目根目录的 `config.yaml`
3. 环境变量

空字符串环境变量会被当作未设置处理，不会覆盖 YAML 或默认值。

## Important Runtime Note

配置加载器和实际运行时不是一回事：

- `load_config()` 的默认 `llm_provider` 仍然是 `mock`
- 但 `build_runtime()` 只接受 `litellm`

因此下面这两类命令的行为不同：

- 只加载配置：`python -m app.startup`
- 真正构建运行时：`python cli.py ...`、`python agentrd_cli.py ...`、`uvicorn app.api_main:app ...`

后者必须提供真实 provider 配置。

## YAML Schema

`config.yaml` 使用扁平结构，字段名与 `AppConfig` 直接对应。

示例：

```yaml
env: dev
default_scenario: data_science
allow_local_execution: true
llm_provider: litellm
llm_model: openai/gpt-4o-mini
costeer_max_rounds: 1
```

建议把 `llm_api_key` 留在环境变量里，不要写入仓库文件。

## Field Mapping

| YAML Key | Env Var | Type | Default in `AppConfig` |
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
| `costeer_max_rounds` | `RD_AGENT_COSTEER_MAX_ROUNDS` | int | `3` |
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

## Real-Provider Guardrails

当 `uses_real_llm_provider(...)` 为真时，运行时会额外施加 guardrail：

- 如果相关字段仍来自默认值，会收紧到保守配置
- 明显超出上限的值会直接报错
- 部分高于保守值但未超过硬上限的配置会产生 warning

当前保守配置：

```text
layer0_n_candidates = 1
layer0_k_forward    = 1
costeer_max_rounds  = 1
sandbox_timeout_sec = 120
max_retries         = 1
```

当前硬上限：

```text
layer0_n_candidates <= 2
layer0_k_forward    <= 2
costeer_max_rounds  <= 2
running.timeout_sec <= 300
proposal/coding/feedback max_retries <= 1
```

## Validation Commands

只验证配置文件可解析：

```bash
python -m app.startup
python -m app.startup --config ./config.yaml
```

验证真实运行时可装配：

```bash
RD_AGENT_LLM_PROVIDER=litellm \
RD_AGENT_LLM_API_KEY=your-api-key \
python agentrd_cli.py health-check --verbose
```
