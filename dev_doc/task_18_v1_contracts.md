# Task-18 V1 Contracts

## Shared DTO module

`service_contracts.py` is the frozen Task-18 source for control-plane DTOs shared by CLI, UI, and future FastAPI surfaces.

Delivered DTOs:

- `RunCreateRequest`
- `RunSummaryResponse`
- `RunControlResponse`
- `RunEventPageResponse`
- `ArtifactListResponse`
- `BranchListResponse`
- `ScenarioManifest`
- `StepOverrideConfig`
- `ErrorResponse`

## Run config snapshot

`RunSession.config_snapshot` persists the effective run configuration in SQLite.

Current snapshot shape:

```json
{
  "scenario": "data_science",
  "stop_conditions": {
    "max_loops": 2,
    "max_steps": null,
    "max_duration_sec": 300
  },
  "step_overrides": {
    "proposal": {},
    "coding": {},
    "running": {
      "timeout_sec": 30
    },
    "feedback": {}
  },
  "scenario_manifest": {
    "scenario_name": "data_science",
    "title": "Data Science",
    "description": "Generate, execute, and evaluate small data-science experiments against a dataset."
  },
  "runtime": {
    "sandbox_timeout_sec": 300,
    "allow_local_execution": false,
    "default_scenario": "data_science"
  }
}
```

## Structured errors

All Task-18 validation failures return:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "entry_input must be an object",
    "field": "entry_input"
  }
}
```

Supported stable error codes:

- `invalid_request`
- `not_found`
- `invalid_state`
- `unsupported_scenario`
- `internal_error`

## Shared scenario manifest source

Scenario capability descriptions are registered once in `plugins.build_default_registry()` and consumed by:

- CLI `health-check --verbose`
- Streamlit UI `load_scenario_manifests()`
- future FastAPI `/scenarios` endpoint
