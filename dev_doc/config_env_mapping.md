# Config Env Mapping (Task-05)

| Env Var | Type | Default | Description |
|---|---|---|---|
| `AGENTRD_ENV` | string | `dev` | Runtime environment |
| `AGENTRD_DEFAULT_SCENARIO` | string | `data_science` | Default scenario plugin |
| `AGENTRD_ARTIFACT_ROOT` | path | `/tmp/rd_agent_artifacts` | Artifact storage root |
| `AGENTRD_WORKSPACE_ROOT` | path | `/tmp/rd_agent_workspace` | Workspace root |
| `AGENTRD_TRACE_STORAGE_PATH` | path | `/tmp/rd_agent_trace/events.jsonl` | Trace event JSONL path |
| `AGENTRD_SQLITE_PATH` | path | `/tmp/rd_agent.sqlite3` | SQLite metadata path |
| `AGENTRD_SANDBOX_TIMEOUT_SEC` | int | `300` | Sandbox timeout in seconds |
| `AGENTRD_LOG_LEVEL` | string | `INFO` | Log verbosity |

## Startup Validation Command

```bash
python3 -m app.startup
```

输出为当前生效配置 JSON。
