# Workspace Manager (Task-07)

`core/execution/workspace_manager.py` 提供：

- `create_workspace`: 创建工作区（可从已有目录复制）
- `copy_workspace`: 复制工作区
- `inject_files`: 注入/覆盖文件
- `create_checkpoint`: 打包工作区为 zip checkpoint
- `restore_checkpoint`: 从 checkpoint 恢复工作区
- `execute_with_recovery`: 执行步骤失败时自动回滚到最近 checkpoint

checkpoint 存储默认复用 `FileCheckpointStore`（`/tmp/rd_agent_checkpoints`）。
