# Storage Foundation (Task-06)

## Interfaces

- `RunMetadataStore`: `create_run/get_run/list_runs`
- `EventMetadataStore`: `append_event/query_events`
- `CheckpointStore`: `save/load/delete/list` checkpoint

接口定义位置：`core/storage/interfaces.py`。

## Implementations

- `SQLiteMetadataStore` (`core/storage/sqlite_store.py`)
  - 表：`runs`, `events`
  - 支持 run 创建/查询、事件追加/查询
- `FileCheckpointStore` (`core/storage/fs_checkpoint_store.py`)
  - 基于文件系统保存 checkpoint 二进制
  - 支持 checkpoint CRUD

## Default Paths

- SQLite: `/tmp/rd_agent.sqlite3`
- Checkpoint root: `/tmp/rd_agent_checkpoints`
