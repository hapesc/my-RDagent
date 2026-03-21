"""V3 orchestration-layer namespace anchor.

This package is reserved for V3-owned control-flow, lifecycle, and recovery
policy. It must depend inward on V3 contracts and ports rather than legacy V2
runtime internals.
"""

BOUNDARY_ROLE = "orchestration"

__all__ = ["BOUNDARY_ROLE"]
