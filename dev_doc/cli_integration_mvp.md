# CLI Entry Integration (Task-14)

## Wiring

`agentrd_cli.py` 已与运行链路打通：

- `run` -> `RunService.create_run/start_run`
- `resume` -> `RunService.resume_run`
- `pause` -> `RunService.pause_run`
- `stop` -> `RunService.stop_run`
- `trace` -> `SQLiteMetadataStore.query_events` + artifact 列表
- `health-check` -> 真实 runtime 检查（sqlite + plugin registry）

装配入口：`app/runtime.py`。

## Demo Flow

`run -> trace -> pause/resume -> stop -> health-check` 已由
`tests/test_task_14_cli_integration.py` 自动验证。
