from __future__ import annotations

from pathlib import Path

from benchmarking.task_registry import materialize_tasks


def test_registry_materializes_smoke_daily_full_profiles() -> None:
    smoke = materialize_tasks("smoke")
    daily = materialize_tasks("daily")
    full = materialize_tasks("full")

    assert smoke
    assert daily
    assert full


def test_registry_emits_required_minimum_fields() -> None:
    tasks = materialize_tasks("smoke")
    task = tasks[0]

    assert task.scenario
    assert task.task_id
    assert task.task_summary
    assert task.source_type in {"local_fixture", "mlebench", "quanteval"}
    assert isinstance(task.tags, tuple)


def test_registry_smoke_uses_local_golden_fixtures() -> None:
    tasks = materialize_tasks("smoke")
    assert all(task.source_type == "local_fixture" for task in tasks)


def test_registry_daily_can_include_external_adapter_tasks_without_importing_corpora() -> None:
    tasks = materialize_tasks("daily")
    source_types = {task.source_type for task in tasks}
    assert "local_fixture" in source_types
    assert "mlebench" in source_types
    assert "quanteval" in source_types


def test_registry_allows_fixture_root_override() -> None:
    fixture_root = Path(__file__).resolve().parents[2] / "tests" / "golden_tasks"
    tasks = materialize_tasks("smoke", fixture_root=fixture_root)
    assert tasks
