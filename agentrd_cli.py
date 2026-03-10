"""MVP CLI contract for Agentic R&D Platform."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from enum import IntEnum
from pathlib import Path
from typing import Any, NoReturn

from app.config import REAL_PROVIDER_SAFE_PROFILE
from app.runtime import build_run_service, build_runtime, resolve_scenario_runtime_profile
from data_models import model_to_dict
from service_contracts import (
    ArtifactDescriptor,
    ArtifactListResponse,
    BranchListResponse,
    BranchSummary,
    ErrorCode,
    ErrorResponse,
    RunControlResponse,
    RunCreateRequest,
    RunEventPageResponse,
    RunSummaryResponse,
    ServiceContractError,
)
from trace_store import TraceTimelineView


class ExitCode(IntEnum):
    """Stable CLI exit codes for MVP."""

    OK = 0
    INVALID_ARGS = 2
    NOT_FOUND = 3
    INVALID_STATE = 4
    INTERNAL_ERROR = 5


def _infer_field_from_text(message: str) -> str | None:
    for token in message.replace(",", " ").split():
        if token.startswith("--"):
            return token[2:].replace("-", "_")
    return None


class CLIArgumentParser(argparse.ArgumentParser):
    """Argument parser that routes validation failures through structured errors."""

    def error(self, message: str) -> NoReturn:
        raise ServiceContractError(
            code=ErrorCode.INVALID_REQUEST,
            message=message,
            field=_infer_field_from_text(message),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = CLIArgumentParser(
        prog="agentrd",
        description="Agentic R&D Platform CLI",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    run_parser = subparsers.add_parser(
        "run",
        help="Create and start a run",
        description="Create a new run session from scenario input.",
    )
    run_parser.add_argument("--config", default=None, help="Path to YAML config file")
    run_parser.add_argument("--scenario", required=True, help="Scenario plugin name")
    run_parser.add_argument("--input", required=True, help="Inline JSON payload or path to JSON file")
    run_parser.add_argument("--loops-per-call", default=1, type=int, help="Iterations to execute now")
    run_parser.add_argument("--max-loops", default=1, type=int, help="Max loops for this run")

    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume an existing run",
        description="Resume a paused/stopped run from latest or specific checkpoint.",
    )
    resume_parser.add_argument("--config", default=None, help="Path to YAML config file")
    resume_parser.add_argument("--run-id", required=True, help="Run identifier")
    resume_parser.add_argument("--checkpoint", required=False, help="Checkpoint identifier")
    resume_parser.add_argument("--loops-per-call", default=1, type=int, help="Iterations to execute now")
    resume_parser.add_argument("--fork-branch", action="store_true", help="Resume on a new fork branch")
    resume_parser.add_argument("--parent-node-id", required=False, help="Parent node for forked resume")

    pause_parser = subparsers.add_parser(
        "pause",
        help="Pause a run",
        description="Pause an active run.",
    )
    pause_parser.add_argument("--config", default=None, help="Path to YAML config file")
    pause_parser.add_argument("--run-id", required=True, help="Run identifier")

    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop a run",
        description="Stop an active run.",
    )
    stop_parser.add_argument("--config", default=None, help="Path to YAML config file")
    stop_parser.add_argument("--run-id", required=True, help="Run identifier")

    trace_parser = subparsers.add_parser(
        "trace",
        help="Query run trace",
        description="Query trace events for a run.",
    )
    trace_parser.add_argument("--config", default=None, help="Path to YAML config file")
    trace_parser.add_argument("--run-id", required=True, help="Run identifier")
    trace_parser.add_argument("--branch-id", required=False, help="Branch identifier")
    trace_parser.add_argument(
        "--format",
        default="json",
        choices=["json", "table"],
        help="Trace output format",
    )

    ui_parser = subparsers.add_parser(
        "ui",
        help="Start trace UI",
        description="Start MVP trace UI server.",
    )
    ui_parser.add_argument("--config", default=None, help="Path to YAML config file")
    ui_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    ui_parser.add_argument("--port", default=8501, type=int, help="Bind port")

    health_parser = subparsers.add_parser(
        "health-check",
        help="Run system health checks",
        description="Run dependency and readiness checks.",
    )
    health_parser.add_argument("--config", default=None, help="Path to YAML config file")
    health_parser.add_argument("--verbose", action="store_true", help="Enable verbose health details")

    return parser


def _load_json_input(raw: str) -> dict[str, Any]:
    path: Path | None = None
    try:
        candidate = Path(raw)
        if candidate.exists():
            path = candidate
    except OSError:
        path = None
    if path is not None:
        try:
            text = path.read_text(encoding="utf-8")
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="--input file must contain valid JSON",
                field="input",
            ) from exc
        if not isinstance(payload, dict):
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="--input must deserialize to a JSON object",
                field="input",
            )
        return payload
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ServiceContractError(
            code=ErrorCode.INVALID_REQUEST,
            message="--input must be inline JSON or an existing JSON file path",
            field="input",
        ) from exc
    if not isinstance(payload, dict):
        raise ServiceContractError(
            code=ErrorCode.INVALID_REQUEST,
            message="--input must deserialize to a JSON object",
            field="input",
        )
    return payload


def _print_json(payload: dict[str, Any], stream=None) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=stream or sys.stdout)


def _print_error(code: str, message: str, field: str | None = None) -> None:
    _print_json(
        ErrorResponse.from_error(ServiceContractError(code=code, message=message, field=field)).to_dict(),
        stream=sys.stderr,
    )


_RUN_REQUEST_RESERVED_KEYS = {
    "scenario",
    "task_summary",
    "run_id",
    "entry_input",
    "stop_conditions",
    "max_loops",
    "max_steps",
    "max_duration_sec",
    "step_overrides",
}


def _build_entry_input(payload: dict[str, Any]) -> dict[str, Any]:
    explicit_entry_input = dict(payload.get("entry_input", {}))
    passthrough = {key: value for key, value in payload.items() if key not in _RUN_REQUEST_RESERVED_KEYS}
    return {**explicit_entry_input, **passthrough}


def _require_scenario_manifest(runtime, scenario: str):
    if scenario not in runtime.plugin_registry.list_scenarios():
        raise ServiceContractError(
            code=ErrorCode.UNSUPPORTED_SCENARIO,
            message=f"unsupported scenario: {scenario}",
            field="scenario",
        )
    manifest = runtime.plugin_registry.get_manifest(scenario)
    if manifest is None:
        raise ServiceContractError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"manifest not configured for scenario: {scenario}",
            field="scenario",
        )
    return manifest


def _build_config_snapshot(runtime, request: RunCreateRequest, manifest) -> dict[str, Any]:
    profile = resolve_scenario_runtime_profile(
        runtime.config,
        manifest.default_step_overrides,
        request.step_overrides,
    )
    return {
        "scenario": request.scenario,
        "stop_conditions": model_to_dict(request.stop_conditions),
        "step_overrides": profile.effective_step_config.to_dict(),
        "requested_step_overrides": request.step_overrides.to_dict(),
        "scenario_manifest": manifest.to_dict(),
        "runtime": {
            "llm_provider": runtime.config.llm_provider,
            "llm_model": runtime.config.llm_model,
            "uses_real_llm_provider": runtime.config.uses_real_llm_provider,
            "sandbox_timeout_sec": runtime.config.sandbox_timeout_sec,
            "allow_local_execution": runtime.config.allow_local_execution,
            "default_scenario": runtime.config.default_scenario,
            "real_provider_safe_profile": dict(REAL_PROVIDER_SAFE_PROFILE),
            "guardrail_warnings": list(profile.guardrail_warnings),
        },
    }


def _emit_guardrail_warnings(config_snapshot: dict[str, Any]) -> None:
    runtime_snapshot = config_snapshot.get("runtime", {})
    for warning in runtime_snapshot.get("guardrail_warnings", []):
        print(f"WARNING: {warning}", file=sys.stderr)


def _artifact_list_response(runtime, run_id: str) -> ArtifactListResponse:
    return ArtifactListResponse(
        run_id=run_id,
        items=[ArtifactDescriptor(path=path) for path in _list_run_artifacts(runtime, run_id)],
    )


def _branch_list_response(runtime, run_id: str) -> BranchListResponse:
    branch_heads = runtime.branch_store.get_branch_heads(run_id)
    return BranchListResponse(
        run_id=run_id,
        items=[
            BranchSummary(branch_id=branch_id, head_node_id=head_node_id)
            for branch_id, head_node_id in sorted(branch_heads.items())
        ],
    )


def _list_run_artifacts(runtime, run_id: str) -> list[str]:
    artifact_paths: list[str] = []
    roots = [
        Path(runtime.config.workspace_root) / run_id,
        Path(runtime.config.artifact_root) / run_id,
    ]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                artifact_paths.append(str(path))
    return sorted(set(artifact_paths))


def _handle_run(args: argparse.Namespace) -> int:
    payload = _load_json_input(args.input)
    runtime = build_runtime(config_path=args.config)
    request = RunCreateRequest.from_dict(
        {
            **payload,
            "scenario": args.scenario,
            "max_loops": payload.get("max_loops", args.max_loops),
        }
    )
    manifest = _require_scenario_manifest(runtime, request.scenario)
    run_service = build_run_service(runtime, request.scenario)
    task_summary = request.task_summary

    run_session = run_service.create_run(
        task_summary=task_summary,
        scenario=request.scenario,
        stop_conditions=request.stop_conditions,
        run_id=request.run_id,
        entry_input=_build_entry_input(payload),
        config_snapshot=_build_config_snapshot(runtime, request, manifest),
    )
    _emit_guardrail_warnings(run_session.config_snapshot)
    context = run_service.start_run(
        run_id=run_session.run_id,
        task_summary=task_summary,
        loops_per_call=args.loops_per_call,
    )
    if context.run_session is None:
        raise RuntimeError("run session missing after start")
    run_summary = RunSummaryResponse.from_run_session(context.run_session)
    artifacts_page = _artifact_list_response(runtime, run_session.run_id)
    _print_json(
        {
            "command": "run",
            "scenario": request.scenario,
            "run_id": run_session.run_id,
            "status": context.run_session.status.value if context.run_session is not None else "UNKNOWN",
            "iteration": context.loop_state.iteration,
            "artifacts": _list_run_artifacts(runtime, run_session.run_id),
            "run": run_summary.to_dict(),
            "artifacts_page": artifacts_page.to_dict(),
        }
    )
    return int(ExitCode.OK)


def _handle_resume(args: argparse.Namespace) -> int:
    runtime = build_runtime(config_path=args.config)
    run_session = runtime.sqlite_store.get_run(args.run_id)
    if run_session is None:
        raise KeyError(f"run not found: {args.run_id}")

    task_summary = str(run_session.entry_input.get("task_summary", "resume"))
    run_service = build_run_service(runtime, run_session.scenario)
    if args.fork_branch:
        run_service.fork_branch(args.run_id, parent_node_id=args.parent_node_id)
    context = run_service.resume_run(
        run_id=args.run_id,
        task_summary=task_summary,
        loops_per_call=args.loops_per_call,
    )
    if context.run_session is None:
        raise RuntimeError("run session missing after resume")
    control = RunControlResponse(
        run_id=args.run_id,
        action="resume",
        status=context.run_session.status.value,
        message="run resumed",
    )
    _print_json(
        {
            "command": "resume",
            "run_id": args.run_id,
            "checkpoint": args.checkpoint,
            "branch_id": context.run_session.active_branch_ids[0] if context.run_session.active_branch_ids else "main",
            "status": context.run_session.status.value,
            "iteration": context.loop_state.iteration,
            "control": control.to_dict(),
        }
    )
    return int(ExitCode.OK)


def _handle_pause(args: argparse.Namespace) -> int:
    runtime = build_runtime(config_path=args.config)
    run_session = runtime.sqlite_store.get_run(args.run_id)
    if run_session is None:
        raise KeyError(f"run not found: {args.run_id}")

    run_service = build_run_service(runtime, run_session.scenario)
    paused = run_service.pause_run(args.run_id)
    control = RunControlResponse(
        run_id=args.run_id,
        action="pause",
        status=paused.status.value,
        message="run paused",
    )
    _print_json(
        {
            "command": "pause",
            "run_id": args.run_id,
            "status": paused.status.value,
            "control": control.to_dict(),
        }
    )
    return int(ExitCode.OK)


def _handle_stop(args: argparse.Namespace) -> int:
    runtime = build_runtime(config_path=args.config)
    run_session = runtime.sqlite_store.get_run(args.run_id)
    if run_session is None:
        raise KeyError(f"run not found: {args.run_id}")

    run_service = build_run_service(runtime, run_session.scenario)
    stopped = run_service.stop_run(args.run_id)
    control = RunControlResponse(
        run_id=args.run_id,
        action="stop",
        status=stopped.status.value,
        message="run stopped",
    )
    _print_json(
        {
            "command": "stop",
            "run_id": args.run_id,
            "status": stopped.status.value,
            "control": control.to_dict(),
        }
    )
    return int(ExitCode.OK)


def _handle_trace(args: argparse.Namespace) -> int:
    runtime = build_runtime(config_path=args.config)
    run_session = runtime.sqlite_store.get_run(args.run_id)
    if run_session is None:
        raise KeyError(f"run not found: {args.run_id}")
    events = runtime.sqlite_store.query_events(run_id=args.run_id, branch_id=args.branch_id)
    nodes = runtime.branch_store.query_nodes(run_id=args.run_id, branch_id=args.branch_id)
    branch_heads = runtime.branch_store.get_branch_heads(args.run_id)
    event_page = RunEventPageResponse(run_id=args.run_id, items=events)
    artifact_page = _artifact_list_response(runtime, args.run_id)
    branch_page = _branch_list_response(runtime, args.run_id)
    run_summary = RunSummaryResponse.from_run_session(run_session)

    if args.format == "table":
        rows = TraceTimelineView().build_rows(events)
        print("timestamp\tevent_type\tbranch_id\tstep_name\tevent_id")
        for row in rows:
            print(f"{row['timestamp']}\t{row['event_type']}\t{row['branch_id']}\t{row['step_name']}\t{row['event_id']}")
        return int(ExitCode.OK)

    _print_json(
        {
            "command": "trace",
            "run_id": args.run_id,
            "branch_id": args.branch_id,
            "format": args.format,
            "events": [event.to_dict() for event in events],
            "nodes": [node.to_dict() for node in nodes],
            "branch_heads": branch_heads,
            "artifacts": _list_run_artifacts(runtime, args.run_id),
            "event_page": event_page.to_dict(),
            "artifacts_page": artifact_page.to_dict(),
            "branches_page": branch_page.to_dict(),
            "run": run_summary.to_dict(),
        }
    )
    return int(ExitCode.OK)


def _handle_ui(args: argparse.Namespace) -> int:
    _print_json(
        {
            "command": "ui",
            "host": args.host,
            "port": args.port,
            "status": "ready",
        }
    )
    return int(ExitCode.OK)


def _handle_health_check(args: argparse.Namespace) -> int:
    runtime = build_runtime(config_path=args.config)
    sqlite_exists = Path(runtime.config.sqlite_path).exists()
    plugin_scenarios = runtime.plugin_registry.list_scenarios()
    manifests = runtime.plugin_registry.list_manifests()

    checks = {
        "sqlite": "ok" if sqlite_exists else "missing",
        "plugin_registry": "ok" if plugin_scenarios else "empty",
    }
    payload = {
        "command": "health-check",
        "status": "ok" if sqlite_exists and plugin_scenarios else "degraded",
        "checks": checks,
    }
    if args.verbose:
        payload["details"] = {
            "sqlite_path": runtime.config.sqlite_path,
            "trace_storage_path": runtime.config.trace_storage_path,
            "registered_scenarios": plugin_scenarios,
            "scenario_manifests": [manifest.to_dict() for manifest in manifests],
        }
    _print_json(payload)
    return int(ExitCode.OK)


def _dispatch_table() -> dict[str, Callable[[argparse.Namespace], int]]:
    return {
        "run": _handle_run,
        "resume": _handle_resume,
        "pause": _handle_pause,
        "stop": _handle_stop,
        "trace": _handle_trace,
        "ui": _handle_ui,
        "health-check": _handle_health_check,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else int(ExitCode.INVALID_ARGS)
        return code

    handlers = _dispatch_table()
    handler = handlers.get(args.command)
    if handler is None:
        _print_error(ErrorCode.INVALID_REQUEST, f"unknown command: {args.command}", field="command")
        return int(ExitCode.INVALID_ARGS)

    try:
        return handler(args)
    except ServiceContractError as exc:
        _print_error(exc.code, str(exc), field=exc.field)
        if exc.code == ErrorCode.NOT_FOUND:
            return int(ExitCode.NOT_FOUND)
        if exc.code == ErrorCode.INVALID_STATE:
            return int(ExitCode.INVALID_STATE)
        if exc.code == ErrorCode.INTERNAL_ERROR:
            return int(ExitCode.INTERNAL_ERROR)
        return int(ExitCode.INVALID_ARGS)
    except FileNotFoundError as exc:
        _print_error(ErrorCode.NOT_FOUND, str(exc))
        return int(ExitCode.NOT_FOUND)
    except KeyError as exc:
        message = exc.args[0] if exc.args else str(exc)
        _print_error(ErrorCode.NOT_FOUND, str(message))
        return int(ExitCode.NOT_FOUND)
    except ValueError as exc:
        _print_error(ErrorCode.INVALID_REQUEST, str(exc), field=_infer_field_from_text(str(exc)))
        return int(ExitCode.INVALID_ARGS)
    except RuntimeError as exc:
        _print_error(ErrorCode.INVALID_STATE, str(exc))
        return int(ExitCode.INVALID_STATE)
    except Exception as exc:  # pragma: no cover - defensive guard for CLI wrapper
        _print_error(ErrorCode.INTERNAL_ERROR, f"internal error: {exc}")
        return int(ExitCode.INTERNAL_ERROR)


if __name__ == "__main__":
    raise SystemExit(main())
