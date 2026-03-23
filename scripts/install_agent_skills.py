#!/usr/bin/env python3
"""Repo-local wrapper for installing standalone runtime bundles and agent skills."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from v3.devtools.skill_install import install_agent_skills


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install standalone runtime bundles and generated skills into Claude and Codex roots.",
    )
    parser.add_argument(
        "--runtime",
        choices=("codex", "claude", "all"),
        default="all",
        help="Which agent runtime to target.",
    )
    parser.add_argument(
        "--scope",
        choices=("local", "global", "all"),
        default="local",
        help="Which install scope to target.",
    )
    parser.add_argument(
        "--mode",
        choices=("link", "copy"),
        default="link",
        help="Install mode. Link is the default and canonical path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        records = install_agent_skills(
            runtime=args.runtime,
            scope=args.scope,
            mode=args.mode,
            repo_root=REPO_ROOT,
        )
    except Exception as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 1

    for record in records:
        line = (
            f"runtime={record.runtime} scope={record.scope} mode={record.mode} "
            f"skill={record.skill_name} action={record.action} destination={record.destination}"
        )
        if record.action == "preserved":
            print(line, file=sys.stderr)
        else:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
