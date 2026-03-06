# Task-20 Per-Step Config

## Goal

Implement the effective config chain:

- scenario defaults
- run-level overrides
- persisted effective snapshot
- trace/UI audit path

## Effective config resolution

The runtime now resolves per-step config as:

`ScenarioManifest.default_step_overrides + RunCreateRequest.step_overrides -> effective step_overrides`

Stored in `RunSession.config_snapshot`:

- `step_overrides`: final effective config
- `requested_step_overrides`: request-time overrides only

## Consumption points

### LLM-backed steps

`LLMAdapter.generate_structured(...)` now accepts `model_config` and consumes:

- `provider`
- `model`
- `temperature`
- `max_tokens`
- `max_retries`

Current mock provider reflects selected model metadata in structured output so tests can verify per-step routing.

### Running step

`DataScienceRunner` passes `step_overrides.running.timeout_sec` into `DockerExecutionBackend.execute(...)`.

The execution trace event also records `timeout_sec` for audit.

## Scenario defaults

Current built-in defaults:

### `data_science`

- `proposal.model = ds-proposal-default`
- `coding.model = ds-coding-default`
- `feedback.model = ds-feedback-default`
- `running.timeout_sec = AGENTRD_SANDBOX_TIMEOUT_SEC`

### `synthetic_research`

- `proposal.model = synthetic-proposal-default`
- `coding.model = synthetic-coding-default`
- `feedback.model = synthetic-feedback-default`
- `running.timeout_sec = AGENTRD_SANDBOX_TIMEOUT_SEC`

## Audit surfaces

Final effective config can be inspected through:

- CLI `trace --format json`
- Streamlit UI `Run Overview`
- persisted `RunSession.config_snapshot` in SQLite

## Example

```bash
python3 agentrd_cli.py run \
  --scenario data_science \
  --input '{
    "task_summary":"override demo",
    "max_loops":1,
    "step_overrides":{
      "proposal":{"model":"proposal-override"},
      "coding":{"model":"coding-override"},
      "running":{"timeout_sec":1},
      "feedback":{"model":"feedback-override"}
    }
  }'
```
