"""Read-only translation boundary for historical V2 inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from v3.contracts.stage import StageKey


@dataclass(frozen=True)
class HistoricalRunRecord:
    """Historical run data that may be translated into V3-owned truth."""

    run_id: str
    scenario_label: str
    title: str
    status: str


@dataclass(frozen=True)
class HistoricalBranchRecord:
    """Historical branch data that may be translated into a V3 branch snapshot."""

    run_id: str
    branch_id: str
    stage_key: StageKey
    source_summary: str | None = None
    artifact_ids: list[str] = field(default_factory=list)


class MigrationPort(Protocol):
    """Read-only access to historical records used for V2-to-V3 translation."""

    def load_run(self, run_id: str) -> HistoricalRunRecord | None: ...

    def load_branch(self, run_id: str, branch_id: str) -> HistoricalBranchRecord | None: ...
