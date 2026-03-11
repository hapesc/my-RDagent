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

部署态运行 `cli.py`、`agentrd_cli.py` 和 API 服务都要求真实 provider：

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=openai/gpt-4o-mini
export RD_AGENT_LLM_API_KEY=your-llm-api-key
```

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
python agentrd_cli.py run \
  --config ./config.yaml \
  --scenario synthetic_research \
  --loops-per-call 1 \
  --max-loops 1 \
  --input '{"task_summary":"deployment smoke","max_loops":1}'
```

4. 如果还要验证执行后端，再加一次：

```bash
python cli.py \
  --config ./config.yaml \
  --scenario data_science \
  --task "classify iris dataset" \
  --max-steps 1
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

默认 runtime 会注册 `quant` manifest，但不会自动配置 `QuantConfig.data_provider`。因此：

- `GET /scenarios` 会列出 `quant`
- 但直接用默认 CLI 或 API 创建 quant run，执行阶段通常会因缺少 data provider 失败

如果你的部署目标包含量化场景，需要在自定义 runtime 中注入 `QuantConfig(data_provider=...)`，或者沿用 `scripts/run_quant_e2e.py` 的装配方式。
