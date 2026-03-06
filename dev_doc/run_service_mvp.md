# RunService + ResumeManager (Task-10)

实现文件：`core/loop/run_service.py`。

## RunService

- `create_run`
- `start_run`
- `pause_run`
- `resume_run`
- `stop_run`
- `get_run`

状态流转控制：`CREATED/RUNNING/PAUSED/COMPLETED/STOPPED/FAILED`。

## ResumeManager

- 基于 checkpoint 列表定位最新 checkpoint
- 计算下一轮 `start_iteration`
- 在 resume 前恢复最新 checkpoint 到工作区

## Process Restart Resume

`tests/test_task_10_run_service.py::test_pause_resume_stop_with_restart` 使用同一 SQLite + checkpoint 目录重建服务实例，验证可从最新 checkpoint 继续执行并完成 run。
