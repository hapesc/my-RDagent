# RDagent Operations Runbook

## Runtime Prerequisites

- Python `3.11+`
- `uv pip install -e ".[all]"` 或至少安装 `llm`、`api`、`ui` 相关 extra
- SQLite 由标准库提供
- Docker 可选，但 `data_science` 场景通常需要 Docker 或 `AGENTRD_ALLOW_LOCAL_EXECUTION=1`
- 真实 LLM provider 配置

示例安装：

```bash
uv venv
uv pip install -e ".[all]"
```

## Configuration Setup

```bash
cp config.example.yaml config.yaml
```

推荐基线：

```yaml
sqlite_path: /tmp/rd_agent_v1/meta.db
workspace_root: /tmp/rd_agent_v1/workspaces
artifact_root: /tmp/rd_agent_v1/artifacts
trace_storage_path: /tmp/rd_agent_v1/trace.jsonl
allow_local_execution: false
```

环境变量覆盖：

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=openai/gpt-4o-mini
export RD_AGENT_LLM_API_KEY=your-key-here
# 如果没有 Docker，但要跑 data_science：
# export AGENTRD_ALLOW_LOCAL_EXECUTION=1
```

如果要走 LiteLLM ChatGPT auth：

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=gpt-5
unset RD_AGENT_LLM_API_KEY
```

说明：

- `chatgpt/...` 与裸 `gpt-*` 会在无 API key 时走 ChatGPT auth
- `openai/...` 仍要求显式 API key

## Startup Sequence

1. 只做配置解析：

```bash
python -m app.startup --config ./config.yaml
```

2. 构建并检查真实运行时：

```bash
python agentrd_cli.py health-check --config ./config.yaml --verbose
```

3. 启动控制面：

```bash
uvicorn app.api_main:app --host 0.0.0.0 --port 8000
```

4. 启动 UI：

```bash
streamlit run ui/trace_ui.py
```

## Smoke Commands

最小 provider smoke，优先使用 `synthetic_research`：

```bash
rdagent run --config ./config.yaml --scenario synthetic_research --task-summary "service smoke"
```

执行链路 smoke，验证沙盒或本地执行：

```bash
rdagent run --config ./config.yaml --task-summary "classify iris dataset"
```

健康检查：

```bash
curl -sS http://127.0.0.1:8000/health
```

## Operational Notes

- **Runtime provider requirement**: `app.startup` 不需要真实 provider，但 CLI/API/control plane 需要。
- **Real-provider guardrails**: 若使用真实 provider，默认 fan-out 和超时会收紧到保守值；超出保守值会给出“执行时间可能会很久”的 warning。
- **Asynchronous execution**: `POST /runs` 立即返回，后台执行由 `RunSupervisor` 持有。
- **State transitions**: `pause` 和 `stop` 是协作式的，会在当前迭代结束后生效。
- **Crash recovery**: 运行状态保存在 SQLite 和 checkpoint 中，恢复依赖显式 `resume`。
- **Strict usefulness gates**: 退出码为 `0` 也不代表候选结果可接受，仍需通过 artifact 校验和场景级 usefulness gate。

## Failure Handling

- **Provider misconfiguration**: 若 `RD_AGENT_LLM_PROVIDER` 缺失或仍为 `mock`，运行时装配直接失败。
- **Execution backend**: `/health` 会报告 `docker_available` 和 `allow_local_execution`；没有 Docker 且未允许本地执行时，执行后端为 `degraded`。
- **Storage**: SQLite 路径不存在时，CLI `health-check` 与控制面的 `/health` 都会降级。
- **Quant scenario**: CLI 路径现在支持 `--data-source /abs/path/ohlcv.csv` 自动装配文件型 provider；HTTP/API 路径如果需要同等能力，仍建议单独设计 provider 装配方案。
