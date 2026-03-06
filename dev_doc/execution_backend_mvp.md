# Execution Backend (Task-08)

## Components

- `ExecutionBackend` protocol
- `DockerExecutionBackend` implementation
- `BackendResult` normalized result model
- `ExecutionStatus`: `SUCCESS/FAILED/TIMEOUT/ERROR`

实现文件：`core/execution/backend.py`。

## Semantics

- Docker 优先：若本机 `docker` 可用且 `prefer_docker=true`，使用容器执行。
- 本地回退：docker 不可用时自动回退到本地 shell 执行。
- Timeout：超时后终止进程并返回 `TIMEOUT`。
- Failure：非 0 退出码返回 `FAILED`。
- Artifact：按 glob 从工作区收集产物路径。

## Trace Integration

每次执行都会写入 `execution.finished` 事件；失败/超时包含标准化字段：

- `status`
- `exit_code`
- `timed_out`
- `artifact_count`
- `stderr`
