"""Test extended data models for FC-2 DAG and FC-3 reasoning traces."""

import pytest
from data_models import (
    BranchState,
    ExplorationGraph,
    NodeRecord,
    model_to_dict,
)


class TestBranchStateEnum:
    """Test BranchState enum definition."""

    def test_branch_state_values(self):
        """BranchState should have exactly 3 values."""
        assert BranchState.ACTIVE.value == "ACTIVE"
        assert BranchState.PRUNED.value == "PRUNED"
        assert BranchState.MERGED.value == "MERGED"

    def test_branch_state_count(self):
        """BranchState should have exactly 3 values total."""
        values = [e.value for e in BranchState]
        assert len(values) == 3
        assert set(values) == {"ACTIVE", "PRUNED", "MERGED"}

    def test_branch_state_serialization(self):
        """BranchState should serialize as string via model_to_dict."""
        state = BranchState.ACTIVE
        serialized = model_to_dict(state)
        assert serialized == "ACTIVE"
        assert isinstance(serialized, str)


class TestExplorationGraphExtended:
    """Test ExplorationGraph extended fields."""

    def test_exploration_graph_has_traces_field(self):
        """ExplorationGraph should have traces field."""
        graph = ExplorationGraph()
        assert hasattr(graph, "traces")
        assert graph.traces == []
        assert isinstance(graph.traces, list)

    def test_exploration_graph_has_branch_scores_field(self):
        """ExplorationGraph should have branch_scores field."""
        graph = ExplorationGraph()
        assert hasattr(graph, "branch_scores")
        assert graph.branch_scores == {}
        assert isinstance(graph.branch_scores, dict)

    def test_exploration_graph_has_branch_states_field(self):
        """ExplorationGraph should have branch_states field."""
        graph = ExplorationGraph()
        assert hasattr(graph, "branch_states")
        assert graph.branch_states == {}
        assert isinstance(graph.branch_states, dict)

    def test_exploration_graph_has_visit_counts_field(self):
        """ExplorationGraph should have visit_counts field."""
        graph = ExplorationGraph()
        assert hasattr(graph, "visit_counts")
        assert graph.visit_counts == {}
        assert isinstance(graph.visit_counts, dict)

    def test_exploration_graph_backward_compatible_construction(self):
        """ExplorationGraph() should work without arguments."""
        graph = ExplorationGraph()
        assert graph.nodes == []
        assert graph.edges == []
        assert graph.traces == []
        assert graph.branch_scores == {}
        assert graph.branch_states == {}
        assert graph.visit_counts == {}

    def test_exploration_graph_with_traces(self):
        """ExplorationGraph should accept traces as tuple adjacency list."""
        traces = [(0, 1), (0, 2), (1, 3)]
        graph = ExplorationGraph(traces=traces)
        assert graph.traces == traces
        assert len(graph.traces) == 3

    def test_exploration_graph_with_branch_scores(self):
        """ExplorationGraph should accept branch_scores dict."""
        scores = {"b1": 0.5, "b2": 0.8}
        graph = ExplorationGraph(branch_scores=scores)
        assert graph.branch_scores == scores

    def test_exploration_graph_with_branch_states(self):
        """ExplorationGraph should accept branch_states dict."""
        states = {"b1": BranchState.ACTIVE, "b2": BranchState.PRUNED}
        graph = ExplorationGraph(branch_states=states)
        assert graph.branch_states == states

    def test_exploration_graph_with_visit_counts(self):
        """ExplorationGraph should accept visit_counts dict."""
        counts = {"n1": 5, "n2": 3}
        graph = ExplorationGraph(visit_counts=counts)
        assert graph.visit_counts == counts


class TestExplorationGraphSerialization:
    """Test serialization of extended ExplorationGraph via model_to_dict."""

    def test_serialization_empty_graph(self):
        """Empty ExplorationGraph should serialize correctly."""
        graph = ExplorationGraph()
        serialized = model_to_dict(graph)
        assert serialized["traces"] == []
        assert serialized["branch_scores"] == {}
        assert serialized["branch_states"] == {}
        assert serialized["visit_counts"] == {}

    def test_serialization_traces(self):
        """Traces (list of tuples) should serialize correctly."""
        traces = [(0, 1), (0, 2), (1, 3)]
        graph = ExplorationGraph(traces=traces)
        serialized = model_to_dict(graph)
        assert serialized["traces"] == traces
        assert len(serialized["traces"]) == 3

    def test_serialization_branch_states_enum(self):
        """Branch states enum values should serialize to strings."""
        graph = ExplorationGraph(
            branch_states={"b1": BranchState.ACTIVE, "b2": BranchState.PRUNED}
        )
        serialized = model_to_dict(graph)
        assert serialized["branch_states"]["b1"] == "ACTIVE"
        assert serialized["branch_states"]["b2"] == "PRUNED"

    def test_serialization_branch_scores(self):
        """Branch scores should serialize correctly."""
        graph = ExplorationGraph(branch_scores={"b1": 0.75, "b2": 0.25})
        serialized = model_to_dict(graph)
        assert serialized["branch_scores"]["b1"] == 0.75
        assert serialized["branch_scores"]["b2"] == 0.25

    def test_serialization_visit_counts(self):
        """Visit counts should serialize correctly."""
        graph = ExplorationGraph(visit_counts={"n1": 10, "n2": 5})
        serialized = model_to_dict(graph)
        assert serialized["visit_counts"]["n1"] == 10
        assert serialized["visit_counts"]["n2"] == 5

    def test_serialization_complex_graph(self):
        """Complex graph with all extended fields should serialize correctly."""
        graph = ExplorationGraph(
            traces=[(0, 1), (1, 2)],
            branch_scores={"b1": 0.8},
            branch_states={"b1": BranchState.ACTIVE},
            visit_counts={"n1": 5},
        )
        serialized = model_to_dict(graph)
        assert serialized["traces"] == [(0, 1), (1, 2)]
        assert serialized["branch_scores"]["b1"] == 0.8
        assert serialized["branch_states"]["b1"] == "ACTIVE"
        assert serialized["visit_counts"]["n1"] == 5


class TestNodeRecordExtended:
    """Test NodeRecord extended fields."""

    def test_node_record_has_score_field(self):
        """NodeRecord should have score field."""
        node = NodeRecord(node_id="n1")
        assert hasattr(node, "score")
        assert node.score is None

    def test_node_record_has_branch_state_field(self):
        """NodeRecord should have branch_state field."""
        node = NodeRecord(node_id="n1")
        assert hasattr(node, "branch_state")
        assert node.branch_state == BranchState.ACTIVE

    def test_node_record_score_optional(self):
        """NodeRecord score should be optional (None by default)."""
        node = NodeRecord(node_id="n1")
        assert node.score is None

    def test_node_record_score_with_value(self):
        """NodeRecord score should accept float values."""
        node = NodeRecord(node_id="n1", score=0.95)
        assert node.score == 0.95

    def test_node_record_branch_state_active_default(self):
        """NodeRecord branch_state should default to ACTIVE."""
        node = NodeRecord(node_id="n1")
        assert node.branch_state == BranchState.ACTIVE

    def test_node_record_branch_state_other_values(self):
        """NodeRecord branch_state should accept other BranchState values."""
        node_pruned = NodeRecord(node_id="n1", branch_state=BranchState.PRUNED)
        assert node_pruned.branch_state == BranchState.PRUNED

        node_merged = NodeRecord(node_id="n1", branch_state=BranchState.MERGED)
        assert node_merged.branch_state == BranchState.MERGED

    def test_node_record_backward_compatible(self):
        """NodeRecord should be backward compatible with existing fields."""
        node = NodeRecord(
            node_id="n1",
            parent_ids=["p1"],
            proposal_id="prop1",
            artifact_id="art1",
            score_id="score1",
        )
        assert node.node_id == "n1"
        assert node.parent_ids == ["p1"]
        assert node.proposal_id == "prop1"
        assert node.artifact_id == "art1"
        assert node.score_id == "score1"
        assert node.score is None
        assert node.branch_state == BranchState.ACTIVE


class TestNodeRecordSerialization:
    """Test serialization of extended NodeRecord via model_to_dict."""

    def test_serialization_node_record(self):
        """NodeRecord should serialize with new fields."""
        node = NodeRecord(node_id="n1", score=0.8, branch_state=BranchState.PRUNED)
        serialized = model_to_dict(node)
        assert serialized["node_id"] == "n1"
        assert serialized["score"] == 0.8
        assert serialized["branch_state"] == "PRUNED"

    def test_serialization_node_record_default_branch_state(self):
        """NodeRecord default branch_state should serialize to ACTIVE string."""
        node = NodeRecord(node_id="n1")
        serialized = model_to_dict(node)
        assert serialized["branch_state"] == "ACTIVE"

    def test_serialization_node_record_null_score(self):
        """NodeRecord with None score should serialize to None."""
        node = NodeRecord(node_id="n1", score=None)
        serialized = model_to_dict(node)
        assert serialized["score"] is None
