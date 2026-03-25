"""V3 entry-layer namespace anchor.

This package is reserved for V3-owned product entrypoints such as skill
surfaces and CLI-oriented tool catalog entrypoints. It must not import legacy
V2 runtime assembly or DTO modules directly.
"""

from .rd_code import rd_code
from .rd_evaluate import rd_evaluate
from .rd_execute import rd_execute
from .rd_propose import rd_propose
from .tool_catalog import call_cli_tool, get_cli_tool, list_cli_tools

BOUNDARY_ROLE = "entry"

__all__ = [
    "BOUNDARY_ROLE",
    "call_cli_tool",
    "get_cli_tool",
    "list_cli_tools",
    "rd_code",
    "rd_evaluate",
    "rd_execute",
    "rd_propose",
]
