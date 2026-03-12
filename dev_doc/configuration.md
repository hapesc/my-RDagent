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
- 真正构建运行时：`python agentrd_cli.py ...`、`uvicorn app.api_main:app ...`

后者必须提供真实 provider 配置。

## YAML Schema

`config.yaml` 由两部分组成：

- 顶层 runtime 配置，字段名与 `AppConfig` 直接对应
- `run_defaults`，作为 `rdagent run` 的默认运行参数

示例：

```yaml
env: dev
default_scenario: data_science
allow_local_execution: true
llm_provider: litellm
llm_model: openai/gpt-4o-mini
costeer_max_rounds: 1

run_defaults:
  scenario: data_science
  stop_conditions:
    max_loops: 1
  entry_input:
    id_column: id
```

建议把 `llm_api_key` 留在环境变量里，不要写入仓库文件。

`litellm` 目前支持两种真实运行模式：

- API key 模式：保留 `llm_api_key`，继续使用常规 provider/model 路径
- ChatGPT auth 模式：`llm_api_key` 为空，且 `llm_model` 为 `chatgpt/...` 或裸 `gpt-*`，runtime 会自动切到 LiteLLM ChatGPT auth

注意：

- `openai/...` 不会在无 key 时自动视为 ChatGPT auth 模型
- 裸 `gpt-*` 只有在 `llm_api_key` 为空时才按 ChatGPT auth 解释

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

## What Each Top-Level Field Means

### Runtime identity and storage

- `env`: runtime environment label such as `dev`, `test`, or `prod`
- `default_scenario`: fallback scenario name when a run request does not explicitly choose one
- `artifact_root`: where artifacts, checkpoints, and archived exceptions are stored
- `workspace_root`: root directory where per-run workspaces are created
- `trace_storage_path`: path for the trace event log
- `sqlite_path`: SQLite database path for persisted metadata

### Execution and logging

- `sandbox_timeout_sec`: default execution timeout for code-running steps
- `allow_local_execution`: whether the runtime may fall back to local execution when Docker is unavailable
- `log_level`: application log verbosity

### LLM configuration

- `llm_provider`: provider name used by runtime assembly; in this repo the real runtime path expects `litellm`
- `llm_api_key`: API key for the selected provider; prefer env injection instead of hardcoding in YAML
- `llm_model`: default model identifier passed into the provider adapter
- `llm_base_url`: optional custom OpenAI-compatible endpoint base URL

### Loop and search controls

- `costeer_max_rounds`: max CoSTEER refinement rounds per iteration
- `mcts_exploration_weight`: exploration weight used by classic MCTS logic
- `mcts_c_puct`: PUCT constant used by the scheduler
- `mcts_reward_mode`: reward aggregation mode for exploration scoring
- `layer0_n_candidates`: how many root candidates are generated at layer 0
- `layer0_k_forward`: how many layer-0 candidates are forwarded downstream
- `prune_threshold`: relative threshold used by branch pruning

### Optional features

- `debug_mode`: enables debug sampling and lighter-weight execution paths where supported
- `debug_sample_fraction`: fraction of data kept when debug sampling is active
- `debug_max_epochs`: training-epoch cap under debug mode
- `enable_hypothesis_storage`: enables hypothesis persistence in MemoryService
- `use_llm_planning`: enables LLM-assisted planning instead of rules-only planning

## `run_defaults`

`run_defaults` 不走环境变量覆盖，当前支持：

```yaml
run_defaults:
  scenario: data_science
  stop_conditions:
    max_loops: 1
    max_steps: null
    max_duration_sec: 300
  step_overrides:
    running:
      timeout_sec: 120
  entry_input:
    id_column: id
    label_column: label
```

规则：

- `null` 表示 unset / 不覆盖
- `step_overrides` 按字段 merge
- `entry_input` 按键 merge
- CLI 显式参数和 `--input` 显式值会覆盖 `run_defaults`

## What Each `run_defaults` Field Means

- `scenario`: default scenario used by `rdagent run` when CLI does not pass `--scenario`
- `stop_conditions.max_loops`: max outer-loop iterations for a run
- `stop_conditions.max_steps`: optional step cap; `null` means unset
- `stop_conditions.max_duration_sec`: total wall-clock budget for a run in seconds
- `step_overrides`: default per-step overrides merged into the run request
- `entry_input`: default scenario input payload merged into each run

Common `entry_input` examples:

- `data_source`: local dataset path for `data_science`
- `id_column`: row identifier column name
- `label_column`: target / label column name

## Real-Provider Guardrails

当 `uses_real_llm_provider(...)` 为真时，运行时会额外施加 guardrail：

- 如果相关字段仍来自默认值，会收紧到保守配置
- 高于保守值时会产生 warning，提示执行时间可能会很久

当前保守配置：

```text
layer0_n_candidates = 1
layer0_k_forward    = 1
costeer_max_rounds  = 1
sandbox_timeout_sec = 120
max_retries         = 1
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
