"""V2 plugin registry for scenario bundle lookup."""

from __future__ import annotations

from v2.plugins.contracts import ScenarioBundle


class PluginRegistry:
    """Stores plugin bundles keyed by scenario name."""

    def __init__(self) -> None:
        self._bundles: dict[str, ScenarioBundle] = {}

    def register(self, name: str, bundle: ScenarioBundle) -> None:
        """Register a scenario bundle.

        Args:
            name: Scenario name.
            bundle: ScenarioBundle with four plugins.

        Raises:
            ValueError: If name is empty.
        """
        key = name.strip()
        if not key:
            raise ValueError("scenario name must not be empty")
        self._bundles[key] = bundle

    def get(self, name: str) -> ScenarioBundle:
        """Retrieve a registered scenario bundle.

        Args:
            name: Scenario name.

        Returns:
            ScenarioBundle: The registered bundle.

        Raises:
            KeyError: If scenario not found.
        """
        key = name.strip()
        if key not in self._bundles:
            available = ", ".join(sorted(self._bundles.keys())) or "<none>"
            raise KeyError(f"unknown scenario '{key}', available: {available}")
        return self._bundles[key]

    def list_scenarios(self) -> list[str]:
        """List all registered scenario names.

        Returns:
            list[str]: Sorted scenario names.
        """
        return sorted(self._bundles.keys())
