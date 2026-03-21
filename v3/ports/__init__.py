"""V3 inward-facing interface namespace anchor.

This package is reserved for ports that V3 orchestration and contracts depend
on. Adapters and compatibility layers may implement these interfaces elsewhere.
"""

from .execution import ExecutionPort, ExecutionStartResult
from .memory_store import MemoryStorePort
from .migration import HistoricalBranchRecord, HistoricalRunRecord, MigrationPort
from .recovery import RecoveryInputs, RecoveryPort
from .state_store import ArtifactRecord, StateStorePort

BOUNDARY_ROLE = "ports"

__all__ = [
    "ArtifactRecord",
    "BOUNDARY_ROLE",
    "ExecutionPort",
    "ExecutionStartResult",
    "HistoricalBranchRecord",
    "HistoricalRunRecord",
    "MemoryStorePort",
    "MigrationPort",
    "RecoveryInputs",
    "RecoveryPort",
    "StateStorePort",
]
