"""MVP CLI contract for Agentic R&D Platform."""

from __future__ import annotations

import argparse
import json
import sys
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.runtime import build_run_service, build_runtime
from data_models import StopConditions
from trace_store import TraceStore, TraceStoreConfig, TraceTimelineView


class ExitCode(IntEnum):
    """Stable CLI exit codes for MVP."""

    OK = 0
    INVALID_ARGS = 2
    NOT_FOUND = 3
    INVALID_STATE = 4
    INTERNAL_ERROR = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentrd",
        description="Agentic R&D Platform MVP CLI",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    run_parser = subparsers.add_parser(
        "run",
        help="Create and start a run",
        description="Create a new run session from scenario input.",
    )
    run_parser.add_argument("--scenario", required=True, help="Scenario plugin name")
    run_parser.add_argument("--input", required=True, help="Inline JSON payload or path to JSON file")
    run_parser.add_argument("--loops-per-call", default=1, type=int, help="Iterations to execute now")
    run_parser.add_argument("--max-loops", default=1, type=int, help="Max loops for this run")

    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume an existing run",
        description="Resume a paused/stopped run from latest or specific checkpoint.",
    )
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
    pause_parser.add_argument("--run-id", required=True, help="Run identifier")

    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop a run",
        description="Stop an active run.",
    )
    stop_parser.add_argument("--run-id", required=True, help="Run identifier")

    trace_parser = subparsers.add_parser(
        "trace",
        help="Query run trace",
        description="Query trace events for a run.",
    )
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
    ui_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    ui_parser.add_argument("--port", default=8501, type=int, help="Bind port")

    health_parser = subparsers.add_parser(
        "health-check",
        help="Run system health checks",
        description="Run dependency and readiness checks.",
    )
    health_parser.add_argument("--verbose", action="store_true", help="Enable verbose health details")

    return parser


def _load_json_input(raw: str) -> Dict[str, Any]:
    path = Path(raw)
    if path.exists():
        text = path.read_text(encoding="utf-8")
        return json.loads(text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("--input must be inline JSON or an existing JSON file path") from exc


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _list_run_artifacts(runtime, run_id: str) -> List[str]:
    artifact_paths: List[str] = []
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
    runtime = build_runtime()
    run_service = build_run_service(runtime, args.scenario)

    task_summary = str(payload.get("task_summary", "cli run"))
    stop_conditions = StopConditions(
        max_loops=int(payload.get("max_loops", args.max_loops)),
        max_steps=None,
        max_duration_sec=int(payload.get("max_duration_sec", 300)),
    )

    run_session = run_service.create_run(
        task_summary=task_summary,
        scenario=args.scenario,
        stop_conditions=stop_conditions,
        run_id=payload.get("run_id"),
    )
    context = run_service.start_run(
        run_id=run_session.run_id,
        task_summary=task_summary,
        loops_per_call=args.loops_per_call,
    )
    _print_json(
        {
            "command": "run",
            "scenario": args.scenario,
            "run_id": run_session.run_id,
            "status": context.run_session.status.value if context.run_session is not None else "UNKNOWN",
            "iteration": context.loop_state.iteration,
            "artifacts": _list_run_artifacts(runtime, run_session.run_id),
        }
    )
    return int(ExitCode.OK)


def _handle_resume(args: argparse.Namespace) -> int:
    runtime = build_runtime()
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
    _print_json(
        {
            "command": "resume",
            "run_id": args.run_id,
            "checkpoint": args.checkpoint,
            "branch_id": context.run_session.active_branch_ids[0] if context.run_session.active_branch_ids else "main",
            "status": context.run_session.status.value if context.run_session is not None else "UNKNOWN",
            "iteration": context.loop_state.iteration,
        }
    )
    return int(ExitCode.OK)


def _handle_pause(args: argparse.Namespace) -> int:
    runtime = build_runtime()
    run_session = runtime.sqlite_store.get_run(args.run_id)
    if run_session is None:
        raise KeyError(f"run not found: {args.run_id}")

    run_service = build_run_service(runtime, run_session.scenario)
    paused = run_service.pause_run(args.run_id)
    _print_json({"command": "pause", "run_id": args.run_id, "status": paused.status.value})
    return int(ExitCode.OK)


def _handle_stop(args: argparse.Namespace) -> int:
    runtime = build_runtime()
    run_session = runtime.sqlite_store.get_run(args.run_id)
    if run_session is None:
        raise KeyError(f"run not found: {args.run_id}")

    run_service = build_run_service(runtime, run_session.scenario)
    stopped = run_service.stop_run(args.run_id)
    _print_json({"command": "stop", "run_id": args.run_id, "status": stopped.status.value})
    return int(ExitCode.OK)


def _handle_trace(args: argparse.Namespace) -> int:
    runtime = build_runtime()
    events = runtime.sqlite_store.query_events(run_id=args.run_id, branch_id=args.branch_id)
    nodes = runtime.branch_store.query_nodes(run_id=args.run_id, branch_id=args.branch_id)
    branch_heads = runtime.branch_store.get_branch_heads(args.run_id)

    if args.format == "table":
        rows = TraceTimelineView().build_rows(events)
        print("timestamp\tevent_type\tbranch_id\tstep_name\tevent_id")
        for row in rows:
            print(
                f"{row['timestamp']}\t{row['event_type']}\t{row['branch_id']}\t{row['step_name']}\t{row['event_id']}"
            )
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
    runtime = build_runtime()
    sqlite_exists = Path(runtime.config.sqlite_path).exists()
    plugin_scenarios = runtime.plugin_registry.list_scenarios()

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
        }
    _print_json(payload)
    return int(ExitCode.OK)


def _dispatch_table() -> Dict[str, Callable[[argparse.Namespace], int]]:
    return {
        "run": _handle_run,
        "resume": _handle_resume,
        "pause": _handle_pause,
        "stop": _handle_stop,
        "trace": _handle_trace,
        "ui": _handle_ui,
        "health-check": _handle_health_check,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else int(ExitCode.INVALID_ARGS)
        return code

    handlers = _dispatch_table()
    handler = handlers.get(args.command)
    if handler is None:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return int(ExitCode.INVALID_ARGS)

    try:
        return handler(args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.NOT_FOUND)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.NOT_FOUND)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.INVALID_ARGS)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.INVALID_STATE)
    except Exception as exc:  # pragma: no cover - defensive guard for CLI wrapper
        print(f"internal error: {exc}", file=sys.stderr)
        return int(ExitCode.INTERNAL_ERROR)


if __name__ == "__main__":
    raise SystemExit(main())
