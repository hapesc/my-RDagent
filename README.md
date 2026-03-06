# Agentic R&D Platform MVP

`Agentic R&D Platform` 的 MVP 实现（Data Science first）。

## MVP 边界

- 包含：单线程 loop、checkpoint/resume、插件化场景、CLI、基础 Trace UI、可观测与脱敏。
- 不包含：REST API、多 worker、高级分支对比（V1 backlog，Task-18）。

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
