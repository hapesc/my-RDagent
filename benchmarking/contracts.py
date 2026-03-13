from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class BenchmarkTask:
    scenario: str
    task_id: str
    task_summary: str
    source_type: str
    inputs: dict[str, Any] = field(default_factory=dict)
    reference_outputs: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()


@dataclass
class BenchmarkRunConfig:
    profile: str
    scenarios: tuple[str, ...]
    upload_results: bool
    rerun_count: int = 1
    enabled_layers: tuple[str, ...] = ()
    output_dir: str | None = None
    compare_baseline: bool = False


@runtime_checkable
class JudgeEvaluator(Protocol):
    def __call__(self, *, inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict:
        ...


@runtime_checkable
class ScenarioEvaluator(Protocol):
    def __call__(self, *, inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict:
        ...


@runtime_checkable
class TraceRecorder(Protocol):
    def record(
        self,
        *,
        run_id: str,
        scenario: str,
        loop_iteration: int,
        last_completed_node: str | None = None,
        next_node: str | None = None,
        checkpoint_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        ...
