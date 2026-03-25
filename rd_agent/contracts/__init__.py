"""V3 public contract namespace anchor.

This package reserves ownership for V3 run, stage, branch, artifact, and
recovery truth. It intentionally avoids importing legacy V2 shared DTOs,
data models, or runtime payloads.
"""

from .artifact import (
    ArtifactKind,
    ArtifactLocator,
    ArtifactProvenance,
    ArtifactReuseLevel,
    ArtifactSnapshot,
)
from .branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from .recovery import RecoveryAssessment, RecoveryDisposition, RecoveryReason, RecoveryReasonCode
from .run import ExecutionMode, RunBoardSnapshot, RunStatus, RunStopReason
from .stage import StageKey, StageSnapshot, StageStatus
from .tool_io import (
    ArtifactCatalogRequest,
    ArtifactCatalogResponse,
    ArtifactListRequest,
    ArtifactListResult,
    BranchCatalogRequest,
    BranchCatalogResponse,
    BranchGetRequest,
    BranchGetResult,
    BranchListRequest,
    BranchListResult,
    RecoveryAssessmentRequest,
    RecoveryAssessmentResponse,
    RecoveryAssessRequest,
    RecoveryAssessResult,
    RunBoardRequest,
    RunBoardResponse,
    RunGetRequest,
    RunGetResult,
    RunStartRequest,
    StageGetRequest,
    StageGetResult,
)

BOUNDARY_ROLE = "contracts"

__all__ = [
    "ArtifactCatalogRequest",
    "ArtifactCatalogResponse",
    "ArtifactListRequest",
    "ArtifactListResult",
    "ArtifactKind",
    "ArtifactLocator",
    "ArtifactProvenance",
    "ArtifactReuseLevel",
    "ArtifactSnapshot",
    "BOUNDARY_ROLE",
    "ExecutionMode",
    "BranchGetRequest",
    "BranchGetResult",
    "BranchCatalogRequest",
    "BranchCatalogResponse",
    "BranchListRequest",
    "BranchListResult",
    "BranchLineage",
    "BranchScore",
    "BranchSnapshot",
    "BranchStatus",
    "RecoveryAssessRequest",
    "RecoveryAssessResult",
    "RecoveryAssessment",
    "RecoveryAssessmentRequest",
    "RecoveryAssessmentResponse",
    "RecoveryDisposition",
    "RecoveryReason",
    "RecoveryReasonCode",
    "RunBoardRequest",
    "RunBoardResponse",
    "RunGetRequest",
    "RunGetResult",
    "RunBoardSnapshot",
    "RunStartRequest",
    "RunStatus",
    "RunStopReason",
    "StageGetRequest",
    "StageGetResult",
    "StageKey",
    "StageSnapshot",
    "StageStatus",
]
