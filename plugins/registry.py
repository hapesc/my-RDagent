"""Plugin registry for scenario bundle lookup."""

from __future__ import annotations

from typing import Callable, Dict, List

from .contracts import PluginBundle

PluginFactory = Callable[[], PluginBundle]


class PluginRegistry:
    """Stores plugin factories keyed by scenario name."""

    def __init__(self) -> None:
        self._factories: Dict[str, PluginFactory] = {}

    def register(self, scenario_name: str, factory: PluginFactory) -> None:
        key = scenario_name.strip()
        if not key:
            raise ValueError("scenario_name must not be empty")
        if key in self._factories:
            raise ValueError(f"plugin already registered: {key}")
        self._factories[key] = factory

    def create_bundle(self, scenario_name: str) -> PluginBundle:
        key = scenario_name.strip()
        try:
            factory = self._factories[key]
        except KeyError as exc:
            available = ", ".join(sorted(self._factories.keys())) or "<none>"
            raise KeyError(f"unknown plugin scenario '{key}', available: {available}") from exc
        return factory()

    def list_scenarios(self) -> List[str]:
        return sorted(self._factories.keys())
