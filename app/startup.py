"""Minimal startup command for configuration validation."""

from __future__ import annotations

import json

from .config import load_config


def main() -> int:
    config = load_config()
    print(json.dumps(config.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
