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

## Configuration setup

The service uses a file-first configuration approach. Start by creating a `config.yaml` from the example:

```bash
cp config.example.yaml config.yaml
```

### Recommended baseline (config.yaml)

```yaml
sqlite_path: /tmp/rd_agent_v1/meta.db
workspace_root: /tmp/rd_agent_v1/workspaces
artifact_root: /tmp/rd_agent_v1/artifacts
trace_storage_path: /tmp/rd_agent_v1/trace.jsonl
sandbox_timeout_sec: 300
allow_local_execution: false
```

### Environment overrides

Use environment variables for secrets or deployment-specific values. They have the highest priority and will override values in `config.yaml`. Note that empty-string environment variables (e.g., `export RD_AGENT_LLM_API_KEY=""`) are treated as unset and will not override config values.

```bash
export RD_AGENT_LLM_API_KEY="your-key-here"
# Optional: force local execution if Docker is unavailable
# export AGENTRD_ALLOW_LOCAL_EXECUTION=1
```

## Startup sequence

1. Validate configuration:

```bash
python3 -m app.startup
# or with a specific file
python3 -m app.startup --config ./config.yaml
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
