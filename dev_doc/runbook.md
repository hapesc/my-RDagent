# RDagent Operations Runbook

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
export RD_AGENT_LLM_PROVIDER="litellm"
export RD_AGENT_LLM_MODEL="gemini/gemini-2.5-flash"
export RD_AGENT_LLM_API_KEY="your-key-here"
# Optional: force local execution if Docker is unavailable
# export AGENTRD_ALLOW_LOCAL_EXECUTION=1
```

## Startup sequence

1. Validate configuration and check real-provider guardrail warnings:

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

Create a run via REST API:

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

Run end-to-end intelligence benchmarks (Requires LLM API Key):

```bash
python3 scripts/e2e_data_science_arena.py
python3 scripts/e2e_resilience_arena.py
```

## Operational notes

- **Real-Provider Bounds**: Real LLM runs default to a conservative profile (`layer0=1/1`, `costeer_max_rounds=1`). You will see guardrail warnings during `app.startup` if you override these manually. This prevents accidental massive fan-out costs.
- **Asynchronous Execution**: `POST /runs` returns immediately; background execution is owned by `RunSupervisor`.
- **State Transitions**: `pause` and `stop` are cooperative and take effect after the current iteration.
- **Crash Recovery**: Service restart does not auto-resume in-flight work; orphaned `RUNNING` runs are rewritten to `PAUSED` and require an explicit `resume` call.
- **Strict Usefulness Gates**: A process exiting with code `0` does not mean success. Artifacts are parsed; if they contain template placeholders (e.g., "synthetic", "placeholder", "TODO") or fail scene-specific statistical validation, they are explicitly marked `INELIGIBLE` and blocked from rewards.

## Failure handling

- **Docker/Sandbox**: If Docker is unavailable and local execution is not opt-in (`allow_local_execution: false`), runs fail closed with a structured error.
- **Storage**: If SQLite or artifact roots are unhealthy, `/health` degrades and should block new production traffic.
- **Resuming**: If a run is paused after a process restart or manual interruption, inspect `entry_input.recovery_required=true` before resuming. Corrupted checkpoints will fail deterministically during the zip extraction phase to prevent silent workspace corruption.
- **LLM Rate Limits**: `LiteLLMProvider` automatically handles transient failures (`ServiceUnavailableError`, `APIConnectionError`) with bounded jittered retries before throwing a permanent exception. Parse failures (due to LLM format drift) emit detailed diagnostics in the trace logs.
