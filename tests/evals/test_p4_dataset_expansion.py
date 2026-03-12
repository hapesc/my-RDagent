"""P4: Validate expanded golden task dataset."""

from __future__ import annotations

import pytest

from tests.golden_tasks.benchmark import load_golden_tasks

pytestmark = pytest.mark.eval

REQUIRED_FIELDS = {"task_id", "scenario", "task_summary", "artifact_type", "expected_properties", "difficulty"}
VALID_SCENARIOS = {"quant", "data_science", "synthetic_research"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_ARTIFACT_TYPES = {"code", "structured_text"}

# Minimum task counts per scenario after expansion
MIN_TASKS_PER_SCENARIO = {"quant": 5, "data_science": 5, "synthetic_research": 4}


def test_all_golden_tasks_have_required_fields():
    tasks = load_golden_tasks()
    for task in tasks:
        missing = REQUIRED_FIELDS - set(task.keys())
        assert not missing, f"Task {task.get('task_id', '?')} missing fields: {missing}"


def test_all_golden_tasks_have_valid_values():
    tasks = load_golden_tasks()
    for task in tasks:
        tid = task["task_id"]
        assert task["scenario"] in VALID_SCENARIOS, f"{tid}: invalid scenario"
        assert task["difficulty"] in VALID_DIFFICULTIES, f"{tid}: invalid difficulty"
        assert task["artifact_type"] in VALID_ARTIFACT_TYPES, f"{tid}: invalid artifact_type"


def test_minimum_tasks_per_scenario():
    tasks = load_golden_tasks()
    counts: dict[str, int] = {}
    for task in tasks:
        s = task["scenario"]
        counts[s] = counts.get(s, 0) + 1
    for scenario, minimum in MIN_TASKS_PER_SCENARIO.items():
        actual = counts.get(scenario, 0)
        assert actual >= minimum, f"Scenario '{scenario}' has {actual} tasks, need >= {minimum}"


def test_no_duplicate_task_ids():
    tasks = load_golden_tasks()
    ids = [t["task_id"] for t in tasks]
    assert len(ids) == len(set(ids)), f"Duplicate task_ids: {[x for x in ids if ids.count(x) > 1]}"


def test_difficulty_distribution():
    """Each scenario should have at least one 'medium' or 'hard' task."""
    tasks = load_golden_tasks()
    by_scenario: dict[str, set[str]] = {}
    for task in tasks:
        by_scenario.setdefault(task["scenario"], set()).add(task["difficulty"])
    for scenario, difficulties in by_scenario.items():
        assert difficulties - {"easy"}, f"Scenario '{scenario}' has only easy tasks"
