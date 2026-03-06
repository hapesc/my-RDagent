# Task-17 Test Matrix

Task-17 验收目标：补齐单元/集成/E2E 验收，并提供可执行验收脚本。

## 1. 验收项映射

| 验收项 | 对应测试 | 类型 |
|---|---|---|
| A1 End-to-End | `tests/test_task_14_cli_integration.py` | 集成/E2E |
| A2 Resume | `tests/test_task_10_run_service.py` | 集成 |
| A4 Sandbox | `tests/test_task_08_execution_backend.py` | 单元/集成 |
| Plugin Contract Test | `tests/test_task_02_plugin_contracts.py` | 单元 |
| Reliability Test | `tests/test_task_17_reliability.py` | 集成 |
| Reproducibility Test | `tests/test_task_17_reproducibility.py` | 集成 |

## 2. 统一验收命令

```bash
./scripts/run_task17_acceptance.sh
```

该脚本内部执行：

```bash
python3 -m unittest \
  tests.test_task_14_cli_integration \
  tests.test_task_10_run_service \
  tests.test_task_08_execution_backend \
  tests.test_task_02_plugin_contracts \
  tests.test_task_17_reliability \
  tests.test_task_17_reproducibility
```

## 3. 全量回归

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```
