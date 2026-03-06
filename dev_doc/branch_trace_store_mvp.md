# TraceStore + Branch Base Model (Task-11)

## Branch DAG Storage

实现：`core/storage/branch_trace_store.py`

- 节点模型：`ExperimentNode`
- 支持父子关系（`parent_node_id`）
- 支持主分支 + fork 分支
- 维护 branch head（`get_branch_heads`）
- 支持历史续跑策略：`create_child_node(..., fork_branch=True)`

## Trace Query

`SQLiteMetadataStore.query_events(run_id, branch_id)` 支持按分支过滤事件。

## Acceptance Mapping

- 同一 run 下主分支与 fork 分支并存：`tests/test_task_11_branch_trace_store.py::test_main_and_fork_branch_can_coexist`
- 分支级 trace 查询：`tests/test_task_11_branch_trace_store.py::test_trace_query_supports_branch_filter`
