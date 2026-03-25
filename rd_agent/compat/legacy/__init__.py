"""Explicit Legacy compatibility seam.

This package is the only reserved place where later phases may translate legacy
runtime, state, or DTO semantics into V3-owned contracts and ports.
"""

BOUNDARY_ROLE = "compat.legacy"

__all__ = ["BOUNDARY_ROLE"]
