# Minimal Deployment (MVP)

目标：在单机环境以最小依赖方式部署并运行 MVP。

## 1. 部署目录与权限

```bash
mkdir -p /tmp/rd_agent_artifacts /tmp/rd_agent_workspace /tmp/rd_agent_trace
```

确保运行用户对以上目录可读写。

## 2. 建议环境变量

```bash
export AGENTRD_ENV=prod
export AGENTRD_DEFAULT_SCENARIO=data_science
export AGENTRD_ARTIFACT_ROOT=/tmp/rd_agent_artifacts
export AGENTRD_WORKSPACE_ROOT=/tmp/rd_agent_workspace
export AGENTRD_TRACE_STORAGE_PATH=/tmp/rd_agent_trace/events.jsonl
export AGENTRD_SQLITE_PATH=/tmp/rd_agent.sqlite3
export AGENTRD_SANDBOX_TIMEOUT_SEC=300
export AGENTRD_LOG_LEVEL=INFO
```

## 3. 部署后 Smoke Check

1. 配置检查：

```bash
python3 -m app.startup
```

2. 健康检查：

```bash
python3 agentrd_cli.py health-check --verbose
```

3. 最小 run 验证：

```bash
python3 agentrd_cli.py run \
  --scenario data_science \
  --loops-per-call 1 \
  --max-loops 1 \
  --input '{"task_summary":"deploy smoke","max_loops":1}'
```

## 4. 验收基线

执行 Task-17 验收脚本：

```bash
./scripts/run_task17_acceptance.sh
```

## 5. 运行与恢复说明

- 元数据：`AGENTRD_SQLITE_PATH`
- checkpoint/artifact：`AGENTRD_ARTIFACT_ROOT`
- workspace：`AGENTRD_WORKSPACE_ROOT`

恢复流程通过 CLI 执行：

```bash
python3 agentrd_cli.py resume --run-id <RUN_ID> --loops-per-call 1
```

## 6. 回滚策略（最小）

1. 停止当前进程调用。
2. 保留当前 `sqlite` 与 artifacts 目录快照。
3. 切换到上一个稳定代码版本并恢复环境变量。
4. 使用 `health-check` 与一次最小 run 重新验证。
