# RDagent Deployment Guide

目标：在单机环境部署当前 `main` 分支，并保证文档中的步骤与源码入口一致。

## 1. 准备目录

```bash
mkdir -p /tmp/rd_agent_artifacts /tmp/rd_agent_workspace /tmp/rd_agent_trace
```

建议把这些路径挂载到持久化存储：

- `artifact_root`
- `workspace_root`
- `trace_storage_path`
- `sqlite_path` 所在目录

## 2. 生成配置文件

```bash
cp config.example.yaml config.yaml
```

推荐基线：

```yaml
env: prod
default_scenario: data_science
artifact_root: /tmp/rd_agent_artifacts
workspace_root: /tmp/rd_agent_workspace
trace_storage_path: /tmp/rd_agent_trace/events.jsonl
sqlite_path: /tmp/rd_agent.sqlite3
allow_local_execution: false
log_level: INFO
```

## 3. 配置真实 LLM Provider

部署态运行 `agentrd_cli.py` 和 API 服务都要求真实 provider：

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=openai/gpt-4o-mini
export RD_AGENT_LLM_API_KEY=your-llm-api-key
```

如果你要使用 LiteLLM ChatGPT auth：

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=gpt-5
unset RD_AGENT_LLM_API_KEY
```

这种模式下，第一次真实请求会触发 LiteLLM 的 ChatGPT device flow 登录。

如果服务器上没有 Docker，但你仍要跑 `data_science` 场景：

```bash
export AGENTRD_ALLOW_LOCAL_EXECUTION=1
```

## 4. Smoke Check

1. 仅检查配置可解析：

```bash
python -m app.startup --config ./config.yaml
```

2. 检查真实运行时：

```bash
python agentrd_cli.py health-check --config ./config.yaml --verbose
```

3. 做一次最小 provider smoke：

```bash
rdagent run --config ./config.yaml --scenario synthetic_research --task-summary "deployment smoke"
```

4. 如果还要验证执行后端，再加一次：

```bash
rdagent run --config ./config.yaml --task-summary "classify iris dataset"
```

## 5. 启动服务

```bash
uvicorn app.api_main:app --host 0.0.0.0 --port 8000
streamlit run ui/trace_ui.py
```

控制面接口：

- `POST /runs`
- `GET /runs/{run_id}`
- `POST /runs/{run_id}/pause`
- `POST /runs/{run_id}/resume`
- `POST /runs/{run_id}/stop`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/artifacts`
- `GET /runs/{run_id}/branches`
- `GET /scenarios`
- `GET /health`

## 6. 恢复说明

系统状态依赖以下路径：

- 元数据：`AGENTRD_SQLITE_PATH`
- 工作区：`AGENTRD_WORKSPACE_ROOT`
- artifacts / checkpoints：`AGENTRD_ARTIFACT_ROOT`

恢复命令：

```bash
python agentrd_cli.py resume --config ./config.yaml --run-id <RUN_ID> --loops-per-call 1
```

## 7. 量化场景部署约束

默认 runtime 会注册 `quant` manifest。对于 CLI 路径：

- `rdagent run --scenario quant --data-source /abs/path/ohlcv.csv` 会自动构建文件型 quant data provider
- 本地文件必须是固定 OHLCV CSV 格式：`date,stock_id,open,high,low,close,volume`

如果你的部署目标包含量化场景的 HTTP/API 创建路径，仍然建议补充显式 provider 装配策略，因为当前自动 provider 装配是面向 CLI 的本地文件路径。
