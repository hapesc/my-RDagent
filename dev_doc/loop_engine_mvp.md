# Loop Engine + Step Executor (Task-09)

## Implementation

- `core/loop/step_executor.py`
  - 六阶段：`propose -> experiment -> coding -> running -> feedback -> record`
  - 每阶段写入事件并创建 step checkpoint
- `core/loop/engine.py`
  - 单线程循环调度
  - 停止条件（按 loop 次数）
  - 异常归档（`/tmp/rd_agent_artifacts/<run_id>/exceptions/*.log`）
  - run 状态持久化（RUNNING/COMPLETED/FAILED）

## Persistence

- 事件：通过 `EventMetadataStore`（当前为 `SQLiteMetadataStore`）按 step 追加。
- run 会话：通过 `RunMetadataStore` 持久化。
- checkpoint：通过 `WorkspaceManager` + `FileCheckpointStore`。

## Acceptance Mapping

- 单线程至少一轮闭环：`tests/test_task_09_loop_engine.py::test_single_thread_completes_one_loop_and_persists`
- 异常归档：`tests/test_task_09_loop_engine.py::test_exception_is_archived_and_run_marked_failed`
