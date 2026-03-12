from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="v2",
        description="V2 Agentic R&D Platform CLI",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    run_parser = subparsers.add_parser("run", help="Create and start a V2 run")
    run_parser.add_argument("--scenario", default="data_science", help="Scenario name")
    run_parser.add_argument("--task-summary", default=None, help="Task summary")
    run_parser.add_argument("--max-loops", default=1, type=int, help="Max loops")
    run_parser.add_argument("--llm-provider", default="mock", help="LLM provider (mock|litellm)")
    run_parser.add_argument("--llm-model", default="gpt-4o-mini", help="LLM model name")

    return parser


def _handle_run(args: argparse.Namespace) -> int:
    runtime_module = importlib.import_module("v2.runtime")
    build_v2_runtime = runtime_module.build_v2_runtime
    config: dict[str, Any] = {
        "llm_provider": args.llm_provider,
        "llm_model": args.llm_model,
        "max_loops": args.max_loops,
    }
    ctx = build_v2_runtime(config)
    run_id = ctx.run_service.create_run(
        {
            "scenario": args.scenario,
            "task_summary": args.task_summary or "",
            "max_loops": args.max_loops,
        }
    )
    ctx.run_service.start_run(run_id)
    status = ctx.run_service.get_status(run_id)
    result = {
        "command": "run",
        "scenario": args.scenario,
        "run_id": run_id,
        "status": status,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    if args.command == "run":
        return _handle_run(args)

    print(f"unknown command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
