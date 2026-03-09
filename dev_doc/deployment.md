# RDagent Deployment Guide

目标：在单机环境以最小依赖方式部署并运行 RDagent。

## 1. 部署目录与权限

```bash
mkdir -p /tmp/rd_agent_artifacts /tmp/rd_agent_workspace /tmp/rd_agent_trace
```

确保运行用户对以上目录可读写。建议生产环境将这些路径挂载到持久化存储。

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
export RD_AGENT_LLM_PROVIDER="litellm"
export RD_AGENT_LLM_MODEL="openai/gpt-4o-mini"
export RD_AGENT_LLM_API_KEY="your-llm-api-key"
# export AGENTRD_ALLOW_LOCAL_EXECUTION=1  # 如果没有 Docker，显式允许本地执行
```

## 3. 部署后基础服务检查 (Smoke Check)

1. 配置检查（默认加载 `./config.yaml`）：

```bash
python3 -m app.startup

# 或显式指定配置文件
python3 -m app.startup --config /path/to/config.yaml
```

2. 静态健康检查：

```bash
python3 agentrd_cli.py health-check --verbose
```

3. Mock 模式空载验证（仅验证进程、沙盒与数据库可写）：

```bash
RD_AGENT_LLM_PROVIDER=mock python3 agentrd_cli.py run \
  --scenario data_science \
  --loops-per-call 1 \
  --max-loops 1 \
  --input '{"task_summary":"deploy smoke","max_loops":1}'
```

## 4. 真实业务能力验收 (E2E Arena Check)

RDagent 配置了严格的 Usefulness Gate（有用性门禁），单纯的代码跑通不足以证明系统可用。在部署完成后，**必须**使用真实模型运行端到端竞技场测试，以确保 API 通信、并发、错误恢复与数学运算能力正常。

1. **微型数据科学精度测试**（验证 Agent 异常值清洗与线性回归准确度）：
```bash
python3 scripts/e2e_data_science_arena.py
```

2. **自我纠错与免疫系统测试**（验证 Agent 遇到报错时的捕获与自我修复能力）：
```bash
python3 scripts/e2e_resilience_arena.py
```

如果以上脚本抛出 `❌ FAILURE`，请检查 `trace_ui` 或 `sqlite` 日志中的 Parse 诊断或 LLM 返回，排查模型幻觉或网络超时问题。

## 5. 运行与恢复说明

系统状态持久化依赖以下挂载点：
- 元数据：`AGENTRD_SQLITE_PATH`
- checkpoint/artifact：`AGENTRD_ARTIFACT_ROOT`
- workspace：`AGENTRD_WORKSPACE_ROOT`

如果进程意外被杀，恢复流程可通过 CLI 执行：

```bash
python3 agentrd_cli.py resume --run-id <RUN_ID> --loops-per-call 1
```

## 6. 回滚策略

1. 停止当前进程或 FastAPI 服务。
2. 备份当前 `sqlite` 与 artifacts 目录快照。
3. 切换到上一个稳定代码版本并恢复环境变量。
4. 使用 `health-check` 与 `e2e_data_science_arena.py` 重新验证。
