# CLI Contract (Task-03, MVP)

## Commands

- `agentrd run --scenario <name> --input <json-or-file>`
- `agentrd resume --run-id <id> [--checkpoint <step>]`
- `agentrd pause --run-id <id>`
- `agentrd stop --run-id <id>`
- `agentrd trace --run-id <id> [--format json|table]`
- `agentrd ui [--host <host>] [--port <port>]`
- `agentrd health-check [--verbose]`

## Exit Codes

- `0` (`OK`): command accepted or completed
- `2` (`INVALID_ARGS`): argument parsing or payload format error
- `3` (`NOT_FOUND`): required resource/file not found
- `4` (`INVALID_STATE`): invalid runtime state
- `5` (`INTERNAL_ERROR`): unexpected internal failure

## Help Contract

- Root help lists all 7 commands.
- Each command has deterministic required/optional arguments.
- `--help` exits with code `0`.
