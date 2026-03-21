"""V3 clean-split namespace anchors.

This package reserves V3-owned architecture boundaries before runtime-shell
implementation begins. V3 core modules must define product-facing entry,
orchestration, contracts, and ports without importing legacy V2 runtime or DTO
modules directly.
"""

__all__ = [
    "entry",
    "orchestration",
    "contracts",
    "ports",
    "compat",
]
