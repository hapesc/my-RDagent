"""Deprecated quick-start CLI shim."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def main(argv=None):
    _ = argv
    logger.error(
        "cli.py is deprecated. Use `rdagent run --config ./config.yaml --task-summary ...` "
        "or `python agentrd_cli.py run ...` instead."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
