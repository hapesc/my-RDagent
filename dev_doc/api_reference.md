# OpenAPI V1 Draft

Task-18 freezes the response and request shapes before the FastAPI control plane is implemented in Task-21.

## Planned endpoints

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

## Component schemas

### `RunCreateRequest`

```json
{
  "scenario": "data_science",
  "task_summary": "evaluate dataset",
  "run_id": "optional-run-id",
  "entry_input": {
    "data_source": "/tmp/train.csv"
  },
  "stop_conditions": {
    "max_loops": 2,
    "max_steps": null,
    "max_duration_sec": 300
  },
  "step_overrides": {
    "proposal": {
      "provider": "openai",
      "model": "gpt-5-mini"
    },
    "coding": {},
    "running": {
      "timeout_sec": 30
    },
    "feedback": {}
  }
}
```

### `RunSummaryResponse`

```json
{
  "run_id": "run-123",
  "scenario": "data_science",
  "status": "RUNNING",
  "active_branch_ids": [
    "main"
  ],
  "created_at": "2026-03-06T12:00:00Z",
  "updated_at": "2026-03-06T12:00:10Z",
  "stop_conditions": {
    "max_loops": 2,
    "max_steps": null,
    "max_duration_sec": 300
  },
  "config_snapshot": {}
}
```

### `RunControlResponse`

```json
{
  "run_id": "run-123",
  "action": "pause",
  "status": "PAUSED",
  "message": "run paused"
}
```

### `RunEventPageResponse`

```json
{
  "run_id": "run-123",
  "items": [],
  "next_cursor": null,
  "limit": 50
}
```

### `ArtifactListResponse`

```json
{
  "run_id": "run-123",
  "items": [
    {
      "path": "/tmp/rd_agent_workspace/run-123/loop-0000/pipeline.py",
      "branch_id": null
    }
  ]
}
```

### `BranchListResponse`

```json
{
  "run_id": "run-123",
  "items": [
    {
      "branch_id": "main",
      "head_node_id": "node-run-123-main-1"
    }
  ]
}
```

### `ScenarioManifest`

```json
{
  "scenario_name": "data_science",
  "title": "Data Science",
  "description": "Generate, execute, and evaluate small data-science experiments against a dataset.",
  "tags": [
    "built-in",
    "python",
    "dataset"
  ],
  "supports_branching": true,
  "supports_resume": true,
  "supports_local_execution": false,
  "supported_step_overrides": [
    "proposal",
    "coding",
    "running",
    "feedback"
  ],
  "default_step_overrides": {
    "proposal": {},
    "coding": {},
    "running": {},
    "feedback": {}
  }
}
```

### `ErrorResponse`

```json
{
  "error": {
    "code": "invalid_request",
    "message": "scenario must not be empty",
    "field": "scenario"
  }
}
```
