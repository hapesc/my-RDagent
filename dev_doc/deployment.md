# Minimal Deployment (MVP)

目标：在单机环境以最小依赖方式部署并运行 MVP。

## 1. 部署目录与权限

```bash
mkdir -p /tmp/rd_agent_artifacts /tmp/rd_agent_workspace /tmp/rd_agent_trace
```

确保运行用户对以上目录可读写。

## 2. 建议配置 (`config.yaml`)

建议从 `config.example.yaml` 复制并修改基础配置：

```bash
cp config.example.yaml config.yaml
```

```yaml
env: prod
default_scenario: data_science
artifact_root: /tmp/rd_agent_artifacts
workspace_root: /tmp/rd_agent_workspace
trace_storage_path: /tmp/rd_agent_trace/events.jsonl
sqlite_path: /tmp/rd_agent.sqlite3
sandbox_timeout_sec: 300
allow_local_execution: false
log_level: INFO
```

### 环境变量覆盖

使用环境变量来设置密钥或特定部署的值。环境变量优先级最高（`defaults < YAML config < env overrides`）。

注意：空字符串环境变量（如 `export RD_AGENT_LLM_API_KEY=""`）会被视为未设置，不会覆盖 YAML 或默认值。

```bash
export RD_AGENT_LLM_API_KEY="your-llm-api-key"
# export AGENTRD_ALLOW_LOCAL_EXECUTION=1  # 如果没有 Docker，显式允许本地执行
```

## 3. 部署后 Smoke Check

1. 配置检查（默认加载 `./config.yaml`）：

```bash
python3 -m app.startup

# 或显式指定配置文件
python3 -m app.startup --config /path/to/config.yaml
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
