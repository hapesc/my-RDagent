#!/usr/bin/env python3
"""Update project version metadata and changelog headings."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
VERSION_LINE_PATTERN = re.compile(r'(?m)^version = "([^"]+)"$')
UNRELEASED_PATTERN = "## [Unreleased]"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump pyproject version and add a dated changelog release header.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files.")
    parser.add_argument("version", help="New semantic version in X.Y.Z format.")
    return parser.parse_args()


def validate_version(version: str) -> None:
    if not SEMVER_PATTERN.fullmatch(version):
        raise ValueError(f"Invalid version '{version}'. Expected semantic version X.Y.Z.")


def update_pyproject(content: str, version: str) -> tuple[str, str]:
    match = VERSION_LINE_PATTERN.search(content)
    if match is None:
        raise ValueError("Could not find version line in pyproject.toml.")
    current_version = match.group(1)
    updated_content = VERSION_LINE_PATTERN.sub(f'version = "{version}"', content, count=1)
    return current_version, updated_content


def update_changelog(content: str, version: str, release_date: str) -> str:
    release_header = f"## [Unreleased]\n\n## [{version}] - {release_date}"
    if UNRELEASED_PATTERN not in content:
        raise ValueError("Could not find '## [Unreleased]' header in CHANGELOG.md.")
    return content.replace(UNRELEASED_PATTERN, release_header, 1)


def main() -> int:
    args = parse_args()

    try:
        validate_version(args.version)
        pyproject_content = PYPROJECT_PATH.read_text()
        changelog_content = CHANGELOG_PATH.read_text()
        current_version, updated_pyproject = update_pyproject(pyproject_content, args.version)
        today = date.today().isoformat()
        updated_changelog = update_changelog(changelog_content, args.version, today)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    changed_files = []
    if pyproject_content != updated_pyproject:
        changed_files.append(f"- {PYPROJECT_PATH.name}: {current_version} -> {args.version}")
    else:
        changed_files.append(f"- {PYPROJECT_PATH.name}: unchanged ({args.version})")

    if changelog_content != updated_changelog:
        changed_files.append(f"- {CHANGELOG_PATH.name}: inserted release header for {args.version} dated {today}")
    else:
        changed_files.append(f"- {CHANGELOG_PATH.name}: unchanged ({args.version} header already present)")

    if args.dry_run:
        print("Dry run: would apply these changes:")
        print("\n".join(changed_files))
        return 0

    PYPROJECT_PATH.write_text(updated_pyproject)
    CHANGELOG_PATH.write_text(updated_changelog)
    print("Updated files:")
    print("\n".join(changed_files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
