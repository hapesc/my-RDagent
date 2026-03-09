"""Minimal startup command for configuration validation."""

from __future__ import annotations

import argparse
import json

from .config import load_config


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Print effective app configuration")
    parser.add_argument("--config", help="Path to YAML config file", default=None)
    args = parser.parse_args(argv if argv is not None else [])
    config = load_config(config_path=args.config)
    print(json.dumps(config.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
