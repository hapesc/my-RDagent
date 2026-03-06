# V1 Service Runbook

## Runtime prerequisites

- Python 3.9+
- SQLite is used implicitly through the stdlib
- For HTTP serving: `fastapi` and `uvicorn`
- For the UI: `streamlit`
- For sandboxed execution: Docker preferred; local execution requires explicit opt-in

Example install:

```bash
python3 -m pip install fastapi uvicorn streamlit
```

## Required environment

```bash
export AGENTRD_SQLITE_PATH=/tmp/rd_agent_v1/meta.db
export AGENTRD_WORKSPACE_ROOT=/tmp/rd_agent_v1/workspaces
export AGENTRD_ARTIFACT_ROOT=/tmp/rd_agent_v1/artifacts
export AGENTRD_TRACE_STORAGE_PATH=/tmp/rd_agent_v1/trace.jsonl
export AGENTRD_SANDBOX_TIMEOUT_SEC=300
export AGENTRD_ALLOW_LOCAL_EXECUTION=0
```

Only set `AGENTRD_ALLOW_LOCAL_EXECUTION=1` when you intentionally accept host-local execution fallback.

## Startup sequence

1. Validate configuration:

```bash
python3 -m app.startup
```

2. Start control plane:

```bash
uvicorn app.api_main:app --host 0.0.0.0 --port 8000
```

3. Start UI in another shell:

```bash
streamlit run ui/trace_ui.py
```

## Smoke commands

Create a run:

```bash
curl -sS -X POST http://127.0.0.1:8000/runs \
  -H 'content-type: application/json' \
  -d '{
    "scenario":"synthetic_research",
    "task_summary":"service smoke",
    "entry_input":{"reference_topics":["llm","eval"]},
    "stop_conditions":{"max_loops":1,"max_duration_sec":60}
  }'
```

Inspect health:

```bash
curl -sS http://127.0.0.1:8000/health
```

## Operational notes

- `POST /runs` returns immediately; background execution is owned by `RunSupervisor`
- `pause` and `stop` are cooperative and take effect after the current iteration
- service restart does not auto-resume in-flight work; orphaned `RUNNING` runs are rewritten to `PAUSED` and require explicit `resume`
- branch and artifact inspection reuse the same DTO shape in control plane and UI

## Failure handling

- if Docker is unavailable and local execution is not opt-in, runs fail closed with a structured error
- if SQLite or artifact roots are unhealthy, `/health` degrades and should block new production traffic
- if a run is paused after process restart, inspect `entry_input.recovery_required=true` before resuming
