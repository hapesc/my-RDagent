"""Tests for V2 plugin protocol contracts and registry."""

import sys
from importlib import import_module
from pathlib import Path

import pytest

root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root))

ProposerPlugin = None
CoderPlugin = None
RunnerPlugin = None
EvaluatorPlugin = None
ScenarioBundle = None
PluginRegistry = None


def setup_module():
    global ProposerPlugin, CoderPlugin, RunnerPlugin, EvaluatorPlugin, ScenarioBundle, PluginRegistry
    contracts = import_module("v2.plugins.contracts")
    registry_mod = import_module("v2.plugins.registry")
    ProposerPlugin = contracts.ProposerPlugin
    CoderPlugin = contracts.CoderPlugin
    RunnerPlugin = contracts.RunnerPlugin
    EvaluatorPlugin = contracts.EvaluatorPlugin
    ScenarioBundle = contracts.ScenarioBundle
    PluginRegistry = registry_mod.PluginRegistry


class TestPluginImports:
    """Test that all plugin contracts are importable."""

    def test_all_plugin_protocols_importable(self):
        """Verify all plugin protocols can be imported."""
        assert ProposerPlugin is not None
        assert CoderPlugin is not None
        assert RunnerPlugin is not None
        assert EvaluatorPlugin is not None

    def test_scenario_bundle_importable(self):
        """Verify ScenarioBundle can be imported."""
        assert ScenarioBundle is not None


class TestScenarioBundleConstruction:
    """Test ScenarioBundle dataclass construction."""

    def test_scenario_bundle_requires_four_plugins(self):
        """ScenarioBundle must accept proposer, coder, runner, evaluator."""

        class MockProposer:
            def propose(self, state: dict) -> dict:
                return {}

        class MockCoder:
            def develop(self, experiment: dict, proposal: dict) -> dict:
                return {}

        class MockRunner:
            def run(self, code: dict) -> dict:
                return {}

        class MockEvaluator:
            def evaluate(self, experiment: dict, result: dict) -> dict:
                return {}

        bundle = ScenarioBundle(
            proposer=MockProposer(),
            coder=MockCoder(),
            runner=MockRunner(),
            evaluator=MockEvaluator(),
        )
        assert bundle.proposer is not None
        assert bundle.coder is not None
        assert bundle.runner is not None
        assert bundle.evaluator is not None

    def test_scenario_bundle_accepts_optional_name(self):
        """ScenarioBundle should accept optional name field."""

        class MockPlugin:
            pass

        bundle = ScenarioBundle(
            proposer=MockPlugin(),
            coder=MockPlugin(),
            runner=MockPlugin(),
            evaluator=MockPlugin(),
            name="test_scenario",
        )
        assert bundle.name == "test_scenario"

    def test_scenario_bundle_default_name_is_empty(self):
        """ScenarioBundle should default name to empty string."""

        class MockPlugin:
            pass

        bundle = ScenarioBundle(
            proposer=MockPlugin(),
            coder=MockPlugin(),
            runner=MockPlugin(),
            evaluator=MockPlugin(),
        )
        assert bundle.name == ""


class TestPluginRegistry:
    """Test PluginRegistry storage and retrieval."""

    def test_registry_register_and_get(self):
        """PluginRegistry should register and retrieve bundles."""
        registry = PluginRegistry()

        class MockPlugin:
            pass

        bundle = ScenarioBundle(
            proposer=MockPlugin(),
            coder=MockPlugin(),
            runner=MockPlugin(),
            evaluator=MockPlugin(),
            name="test_scenario",
        )

        registry.register("test_scenario", bundle)
        retrieved = registry.get("test_scenario")
        assert retrieved is bundle

    def test_registry_get_nonexistent_raises_key_error(self):
        """PluginRegistry.get() should raise KeyError for unknown scenario."""
        registry = PluginRegistry()

        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_registry_list_scenarios(self):
        """PluginRegistry should list registered scenario names."""
        registry = PluginRegistry()

        class MockPlugin:
            pass

        bundle1 = ScenarioBundle(
            proposer=MockPlugin(),
            coder=MockPlugin(),
            runner=MockPlugin(),
            evaluator=MockPlugin(),
        )
        bundle2 = ScenarioBundle(
            proposer=MockPlugin(),
            coder=MockPlugin(),
            runner=MockPlugin(),
            evaluator=MockPlugin(),
        )

        registry.register("scenario1", bundle1)
        registry.register("scenario2", bundle2)

        scenarios = registry.list_scenarios()
        assert "scenario1" in scenarios
        assert "scenario2" in scenarios
        assert len(scenarios) == 2
