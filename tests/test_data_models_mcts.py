"""Test MCTS statistics fields on NodeRecord."""

from data_models import BranchState, NodeRecord


class TestNodeRecordMCTSFields:
    """Test MCTS statistics fields on NodeRecord."""

    def test_noderecord_visits_default_is_zero(self):
        """visits field should default to 0."""
        node = NodeRecord(node_id="test_node")
        assert hasattr(node, "visits")
        assert node.visits == 0
        assert isinstance(node.visits, int)

    def test_noderecord_total_value_default_is_zero(self):
        """total_value field should default to 0.0."""
        node = NodeRecord(node_id="test_node")
        assert hasattr(node, "total_value")
        assert node.total_value == 0.0
        assert isinstance(node.total_value, float)

    def test_noderecord_avg_value_default_is_zero(self):
        """avg_value field should default to 0.0."""
        node = NodeRecord(node_id="test_node")
        assert hasattr(node, "avg_value")
        assert node.avg_value == 0.0
        assert isinstance(node.avg_value, float)

    def test_update_stats_single_reward(self):
        """update_stats(reward) should increment visits and update values."""
        node = NodeRecord(node_id="test_node")
        node.update_stats(0.5)
        assert node.visits == 1
        assert node.total_value == 0.5
        assert node.avg_value == 0.5

    def test_update_stats_multiple_rewards(self):
        """update_stats called multiple times should accumulate correctly."""
        node = NodeRecord(node_id="test_node")
        node.update_stats(0.5)
        node.update_stats(0.3)
        assert node.visits == 2
        assert node.total_value == 0.8
        assert abs(node.avg_value - 0.4) < 1e-9

    def test_update_stats_with_zero_reward(self):
        """update_stats(0.0) should still increment visits."""
        node = NodeRecord(node_id="test_node")
        node.update_stats(0.0)
        assert node.visits == 1
        assert node.total_value == 0.0
        assert node.avg_value == 0.0

    def test_update_stats_with_negative_reward(self):
        """update_stats should handle negative rewards."""
        node = NodeRecord(node_id="test_node")
        node.update_stats(-0.2)
        assert node.visits == 1
        assert node.total_value == -0.2
        assert node.avg_value == -0.2

    def test_update_stats_mixed_rewards(self):
        """update_stats with mixed positive and negative rewards."""
        node = NodeRecord(node_id="test_node")
        node.update_stats(1.0)
        node.update_stats(-0.5)
        node.update_stats(0.5)
        assert node.visits == 3
        assert node.total_value == 1.0
        assert abs(node.avg_value - (1.0 / 3.0)) < 1e-9

    def test_noderecord_backward_compat_minimal(self):
        """NodeRecord created with only node_id should still work."""
        node = NodeRecord(node_id="backward_compat_node")
        assert node.node_id == "backward_compat_node"
        assert node.parent_ids == []
        assert node.proposal_id is None
        assert node.artifact_id is None
        assert node.score_id is None
        assert node.score is None
        assert node.branch_state == BranchState.ACTIVE
        assert node.visits == 0
        assert node.total_value == 0.0
        assert node.avg_value == 0.0

    def test_noderecord_backward_compat_with_existing_fields(self):
        """NodeRecord with existing fields should work without new fields."""
        node = NodeRecord(
            node_id="test_node",
            parent_ids=["parent1", "parent2"],
            proposal_id="prop123",
            artifact_id="art456",
            score_id="score789",
            score=0.95,
            branch_state=BranchState.PRUNED,
        )
        assert node.node_id == "test_node"
        assert node.parent_ids == ["parent1", "parent2"]
        assert node.proposal_id == "prop123"
        assert node.artifact_id == "art456"
        assert node.score_id == "score789"
        assert node.score == 0.95
        assert node.branch_state == BranchState.PRUNED
        assert node.visits == 0
        assert node.total_value == 0.0
        assert node.avg_value == 0.0

    def test_noderecord_with_all_fields_specified(self):
        """NodeRecord can be created with all fields including new MCTS fields."""
        node = NodeRecord(
            node_id="test_node",
            parent_ids=["parent1"],
            proposal_id="prop123",
            artifact_id="art456",
            score_id="score789",
            score=0.95,
            branch_state=BranchState.ACTIVE,
            visits=5,
            total_value=2.5,
            avg_value=0.5,
        )
        assert node.node_id == "test_node"
        assert node.visits == 5
        assert node.total_value == 2.5
        assert node.avg_value == 0.5
        assert node.branch_state == BranchState.ACTIVE

    def test_update_stats_three_calls(self):
        """Three calls to update_stats should be calculated correctly."""
        node = NodeRecord(node_id="test_node")
        node.update_stats(0.6)
        node.update_stats(0.4)
        node.update_stats(0.0)
        assert node.visits == 3
        assert node.total_value == 1.0
        assert abs(node.avg_value - (1.0 / 3.0)) < 1e-9

    def test_update_stats_large_reward(self):
        """update_stats should handle large reward values."""
        node = NodeRecord(node_id="test_node")
        node.update_stats(100.0)
        node.update_stats(200.0)
        assert node.visits == 2
        assert node.total_value == 300.0
        assert node.avg_value == 150.0
