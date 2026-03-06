"""Plugin registry for scenario bundle lookup."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .contracts import PluginBundle
from service_contracts import ScenarioManifest

PluginFactory = Callable[[], PluginBundle]


class PluginRegistry:
    """Stores plugin factories keyed by scenario name."""

    def __init__(self) -> None:
        self._factories: Dict[str, PluginFactory] = {}
        self._manifests: Dict[str, ScenarioManifest] = {}

    def register(
        self,
        scenario_name: str,
        factory: PluginFactory,
        manifest: Optional[ScenarioManifest] = None,
    ) -> None:
        key = scenario_name.strip()
        if not key:
            raise ValueError("scenario_name must not be empty")
        if key in self._factories:
            raise ValueError(f"plugin already registered: {key}")
        self._factories[key] = factory
        if manifest is not None:
            self._manifests[key] = manifest

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

    def get_manifest(self, scenario_name: str) -> Optional[ScenarioManifest]:
        return self._manifests.get(scenario_name.strip())

    def list_manifests(self) -> List[ScenarioManifest]:
        return [self._manifests[key] for key in sorted(self._manifests.keys())]
