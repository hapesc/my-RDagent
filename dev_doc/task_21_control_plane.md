# Task-21 Control Plane

## Delivered

- FastAPI-compatible control plane entrypoint: `app/api_main.py`
- Background `RunSupervisor`
- Endpoints:
  - `POST /runs`
  - `GET /runs/{run_id}`
  - `POST /runs/{run_id}/pause`
  - `POST /runs/{run_id}/resume`
  - `POST /runs/{run_id}/stop`
  - `GET /runs/{run_id}/events`
  - `GET /runs/{run_id}/artifacts`
  - `GET /runs/{run_id}/branches`
  - `GET /scenarios`
  - `GET /health`

## Runtime model

`RunSupervisor` runs the loop in a background thread and advances one loop iteration per cycle. This keeps the control plane responsive while still using the existing `RunService` and loop engine unchanged.

Control actions are cooperative:

- `pause` stops after the current iteration
- `stop` stops after the current iteration
- `resume` restarts the background worker explicitly

## Restart semantics

Supervisor initialization scans persisted runs and converts orphaned `RUNNING` sessions to `PAUSED`, marking:

```json
{
  "recovery_required": true
}
```

This satisfies the V1 requirement that service restart does not auto-resume in-flight runs.

## Compatibility note

The repository currently includes a small compatibility layer in `app/fastapi_compat.py` so Task-21 can be tested without external `fastapi/uvicorn` dependencies installed. If real FastAPI is present, the control plane imports it directly.
