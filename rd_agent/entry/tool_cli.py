"""CLI for the V3 skill/tool catalog."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from rd_agent.entry.tool_catalog import get_cli_tool, list_cli_tools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rdagent-tool",
        description="Inspect the V3 skill and CLI tool catalog.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    subparsers.add_parser("list", help="List the available V3 CLI tools")

    describe_parser = subparsers.add_parser("describe", help="Describe one V3 CLI tool")
    describe_parser.add_argument("name", help="Tool name, for example rd_run_start")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "list":
            payload = list_cli_tools()
        elif args.command == "describe":
            payload = get_cli_tool(args.name)
        else:
            parser.error(f"unknown command: {args.command}")
            return 2
    except KeyError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 3

    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
