from __future__ import annotations

from typing import Any

try:
    from langgraph.types import task
except ImportError:
    # Fallback: no-op decorator if langgraph.types.task unavailable
    def task(fn):  # type: ignore[misc]
        return fn


@task
def select_exploration_node(scheduler: Any, exploration_graph: Any) -> str | None:
    """MCTS node selection, cached by @task on resume."""
    if scheduler is None or exploration_graph is None:
        return None
    return scheduler.select_node(exploration_graph)
