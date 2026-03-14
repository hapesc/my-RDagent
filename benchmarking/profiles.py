"""Benchmark profile definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkProfile:
    name: str
    scenarios: tuple[str, ...]
    enabled_layers: tuple[str, ...]
    rerun_count: int
    upload_results_by_default: bool
    requires_external_corpora: bool
    max_loops: int
    self_correction_rounds: int


_PROFILES: dict[str, BenchmarkProfile] = {
    "smoke": BenchmarkProfile(
        name="smoke",
        scenarios=("data_science", "quant"),
        enabled_layers=("rules", "scenario", "judge"),
        rerun_count=1,
        upload_results_by_default=False,
        requires_external_corpora=False,
        max_loops=6,
        self_correction_rounds=2,
    ),
    "daily": BenchmarkProfile(
        name="daily",
        scenarios=("data_science", "quant", "synthetic_research"),
        enabled_layers=("rules", "scenario", "judge"),
        rerun_count=2,
        upload_results_by_default=False,
        requires_external_corpora=False,
        max_loops=8,
        self_correction_rounds=3,
    ),
    "full": BenchmarkProfile(
        name="full",
        scenarios=("data_science", "quant", "synthetic_research"),
        enabled_layers=("rules", "scenario", "judge"),
        rerun_count=3,
        upload_results_by_default=True,
        requires_external_corpora=True,
        max_loops=10,
        self_correction_rounds=4,
    ),
}


def list_profiles() -> tuple[str, ...]:
    return tuple(_PROFILES.keys())


def get_profile(name: str) -> BenchmarkProfile:
    try:
        return _PROFILES[name]
    except KeyError as exc:
        raise KeyError(f"unknown benchmark profile: {name}") from exc
