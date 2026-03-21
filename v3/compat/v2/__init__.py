"""Explicit V2 compatibility seam anchor for V3.

This package is the only reserved place where later phases may translate V2
runtime, state, or DTO semantics into V3-owned contracts and ports.
"""

BOUNDARY_ROLE = "compat.v2"

__all__ = ["BOUNDARY_ROLE"]
