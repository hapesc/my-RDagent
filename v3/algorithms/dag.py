"""Pure DAG traversal helpers for exploration topology."""

from __future__ import annotations

from collections import deque


def get_ancestors(node_id: str, parent_map: dict[str, list[str]]) -> set[str]:
    """Collect all ancestor node IDs reachable from `node_id`."""

    visited: set[str] = set()
    queue = deque(parent_map.get(node_id, []))
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(parent_map.get(current, []))
    return visited


def get_descendants(node_id: str, child_map: dict[str, list[str]]) -> set[str]:
    """Collect all descendant node IDs reachable from `node_id`."""

    visited: set[str] = set()
    queue = deque(child_map.get(node_id, []))
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(child_map.get(current, []))
    return visited


def get_frontier(parent_map: dict[str, list[str]], all_node_ids: set[str]) -> set[str]:
    """Return leaf nodes that do not act as a parent of any other node."""

    child_map: dict[str, list[str]] = {node_id: [] for node_id in all_node_ids}
    for child_id, parent_ids in parent_map.items():
        child_map.setdefault(child_id, [])
        for parent_id in parent_ids:
            child_map.setdefault(parent_id, []).append(child_id)
    return {node_id for node_id in all_node_ids if not child_map.get(node_id)}


def get_depth(node_id: str, parent_map: dict[str, list[str]]) -> int:
    """Compute the longest distance from any root to `node_id`."""

    memo: dict[str, int] = {}

    def _depth(current: str, visiting: set[str]) -> int:
        if current in memo:
            return memo[current]
        if current in visiting:
            raise ValueError(f"cycle detected while computing depth for {current}")
        visiting.add(current)
        parents = parent_map.get(current, [])
        depth = 0 if not parents else 1 + max(_depth(parent_id, visiting) for parent_id in parents)
        visiting.remove(current)
        memo[current] = depth
        return depth

    return _depth(node_id, set())


__all__ = ["get_ancestors", "get_depth", "get_descendants", "get_frontier"]
