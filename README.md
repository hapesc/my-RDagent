# Agentic R&D Platform V1

`Agentic R&D Platform` 的当前实现已达到 PRD V1：正式双场景入口、per-step 配置、FastAPI 控制面、branch-aware UI、恢复与分支查询链路均已接通。

## V1 边界

- 包含：单线程 loop、checkpoint/resume、插件化双场景、CLI、FastAPI 控制面、branch-aware Trace UI、可观测与脱敏、per-step override 审计。
- 不包含：Human Instructions、Knowledge Base、多 worker、审批流、高级分支对比。

## 快速启动

1. 检查配置加载：

```bash
python3 -m app.startup
```

2. 启动一次 run：

```bash
export AGENTRD_ALLOW_LOCAL_EXECUTION=1  # 仅在需要本地执行时显式开启
python3 agentrd_cli.py run \
  --scenario data_science \
  --loops-per-call 1 \
  --max-loops 1 \
  --input '{"task_summary":"quick start","max_loops":1}'
```

3. 查询 trace：

```bash
python3 agentrd_cli.py trace --run-id <RUN_ID> --format table
```

4. 启动 V1 控制面与 branch-aware UI（需要额外安装 `fastapi` / `uvicorn` / `streamlit`）：

```bash
uvicorn app.api_main:app --host 127.0.0.1 --port 8000
streamlit run ui/trace_ui.py
```

## 支持场景

- `data_science`: 生成并执行小型数据科学实验。
- `synthetic_research`: 生成轻量研究 brief 与 findings，作为正式的第二场景入口。

`health-check --verbose` 会返回共享的场景 manifest 列表：

```bash
python3 agentrd_cli.py health-check --verbose
```

`synthetic_research` 最小运行示例：

```bash
python3 agentrd_cli.py run \
  --scenario synthetic_research \
  --loops-per-call 1 \
  --input '{"task_summary":"summarize LLM eval directions","reference_topics":["alignment","benchmarking"],"max_loops":1}'
```

## Per-Step Overrides

`Task-20` 起支持“场景默认值 + run 覆盖”的 per-step 配置：

- `proposal`
- `coding`
- `running.timeout_sec`
- `feedback`

示例：

```bash
python3 agentrd_cli.py run \
  --scenario data_science \
  --input '{
    "task_summary":"override demo",
    "max_loops":1,
    "step_overrides":{
      "proposal":{"model":"proposal-override"},
      "coding":{"model":"coding-override"},
      "running":{"timeout_sec":30},
      "feedback":{"model":"feedback-override"}
    }
  }'
```

审计本次 run 的最终生效配置：

```bash
python3 agentrd_cli.py trace --run-id <RUN_ID> --format json
```

Trace 输出中的 `run.config_snapshot.step_overrides` 为最终生效配置，`requested_step_overrides` 为本次请求覆盖。

## 验收测试

- Task-17 验收矩阵：

```bash
./scripts/run_task17_acceptance.sh
```

- 全量测试：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## 交付文档

- 运行手册：`dev_doc/runbook_mvp.md`
- 最小部署：`dev_doc/deploy_minimal_mvp.md`
- Task-17 测试矩阵：`dev_doc/task_17_test_matrix.md`
- Task-18 契约：`dev_doc/task_18_v1_contracts.md`
- Task-19 场景说明：`dev_doc/task_19_synthetic_research.md`
- Task-20 per-step 配置：`dev_doc/task_20_per_step_config.md`
- Task-21 控制面：`dev_doc/task_21_control_plane.md`
- Task-22 branch-aware UI：`dev_doc/task_22_branch_aware_ui.md`
- Task-23 V1 验收：`dev_doc/task_23_v1_acceptance.md`
- V1 服务 runbook：`dev_doc/runbook_v1_service.md`
