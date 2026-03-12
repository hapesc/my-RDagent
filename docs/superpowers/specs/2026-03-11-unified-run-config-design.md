# Unified Run Config Design

## Goal

Unify stable run configuration in `config.yaml` and narrow execution to a single supported runtime entrypoint: `rdagent run` / `python agentrd_cli.py run`.

## Decisions

- Keep top-level `config.yaml` fields for runtime/deployment settings.
- Add `run_defaults` to `config.yaml` for default run behavior:
  - `scenario`
  - `stop_conditions`
  - `step_overrides`
  - `entry_input`
- Keep `null` semantics as "unset / do not override", never "infinite" or "disabled".
- Make `agentrd_cli.py run` the only supported run path.
- Deprecate `cli.py` and stop using it for actual execution.
- Keep `--input` for compatibility, but treat it as an advanced override path rather than the primary UX.
- Add high-frequency CLI flags such as `--task-summary` and `--data-source`.

## Merge Order

1. Code defaults
2. Top-level runtime config from `config.yaml`
3. `config.yaml.run_defaults`
4. Explicit CLI flags
5. Explicit `--input` payload values

Merge semantics:

- `step_overrides` merge field-by-field
- `entry_input` merges key-by-key
- explicit values always win over defaults

## Non-Goals

- No redesign of control-plane HTTP contracts in this change
- No change to execution backend mounting behavior
- No removal of `--input` compatibility
