# Runbook (MVP)

本手册用于本地运行 `Agentic R&D Platform MVP`（单机模式）。

## 1. 前置条件

- Python 3.9+
- 本地 shell 环境（macOS/Linux）
- 可选：Docker（执行后端优先使用）
- 可选：Streamlit（Trace UI）

## 2. 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `AGENTRD_ENV` | `dev` | 运行环境标识 |
| `AGENTRD_DEFAULT_SCENARIO` | `data_science` | 默认场景 |
| `AGENTRD_ARTIFACT_ROOT` | `/tmp/rd_agent_artifacts` | 产物根目录 |
| `AGENTRD_WORKSPACE_ROOT` | `/tmp/rd_agent_workspace` | workspace 根目录 |
| `AGENTRD_TRACE_STORAGE_PATH` | `/tmp/rd_agent_trace/events.jsonl` | jsonl trace 路径 |
| `AGENTRD_SQLITE_PATH` | `/tmp/rd_agent.sqlite3` | SQLite 元数据库 |
| `AGENTRD_SANDBOX_TIMEOUT_SEC` | `300` | sandbox timeout（秒） |
| `AGENTRD_ALLOW_LOCAL_EXECUTION` | `false` | 是否显式允许宿主机本地执行 |
| `AGENTRD_LOG_LEVEL` | `INFO` | 日志级别 |

配置校验命令：

```bash
python3 -m app.startup
```

## 3. 标准操作流程

### 3.1 创建并执行 run

```bash
python3 agentrd_cli.py run \
  --scenario data_science \
  --loops-per-call 1 \
  --max-loops 2 \
  --input '{"task_summary":"runbook demo","max_loops":2}'
```

### 3.2 查询 trace

```bash
python3 agentrd_cli.py trace --run-id <RUN_ID> --format json
python3 agentrd_cli.py trace --run-id <RUN_ID> --format table
```

### 3.3 控制 run

```bash
python3 agentrd_cli.py pause --run-id <RUN_ID>
python3 agentrd_cli.py resume --run-id <RUN_ID> --loops-per-call 1
python3 agentrd_cli.py stop --run-id <RUN_ID>
```

### 3.4 健康检查

```bash
python3 agentrd_cli.py health-check --verbose
```

## 4. Trace UI

安装并启动：

```bash
pip install streamlit
streamlit run ui/trace_ui.py
```

## 5. 常见问题

1. `run not found`  
确认 `AGENTRD_SQLITE_PATH` 与 run 创建时一致。

2. `streamlit is required for UI`  
安装 `streamlit` 后重试。

3. 期望 Docker 执行但实际为本地执行  
当前默认不会静默回退到本地执行；仅当 `AGENTRD_ALLOW_LOCAL_EXECUTION=1` 时才会本地执行。若希望容器执行，确认本机有 `docker` 命令且插件配置 `prefer_docker=true`。
