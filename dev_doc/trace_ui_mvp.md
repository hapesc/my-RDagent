# Trace UI (Task-15)

实现：`ui/trace_ui.py`

功能：

- 时间线（Timeline）
- 事件详情（Step/Event Payload）
- 日志/指标/产物查看
- 增量刷新（auto refresh）

启动方式：

```bash
streamlit run ui/trace_ui.py
```

数据来源：

- 事件：`SQLiteMetadataStore.query_events`
- 产物：`workspace_root/<run_id>` 与 `artifact_root/<run_id>`
