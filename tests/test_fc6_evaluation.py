"""Tests for FC-6 — stratified splitter, ValidationSelector, aggregate scoring."""
import unittest
from importlib import import_module

from data_models import DataSplitManifest, EvalResult, ExecutionResult, Score


class TestStratifiedSplitter(unittest.TestCase):
    """90/10 stratified train/test splitting."""

    def test_split_ratio_90_10(self):
        """Default 90/10 split."""
        from evaluation_service import StratifiedSplitter

        s = StratifiedSplitter(train_ratio=0.9, test_ratio=0.1)
        ids = [f"id-{i}" for i in range(100)]
        manifest = s.split(ids)
        self.assertEqual(len(manifest.train_ids), 90)
        self.assertEqual(len(manifest.test_ids), 10)
        self.assertEqual(len(manifest.val_ids), 0)

    def test_split_no_overlap(self):
        """Train and test sets don't overlap."""
        from evaluation_service import StratifiedSplitter

        s = StratifiedSplitter()
        ids = [f"id-{i}" for i in range(100)]
        manifest = s.split(ids)
        train_set = set(manifest.train_ids)
        test_set = set(manifest.test_ids)
        self.assertEqual(len(train_set & test_set), 0)

    def test_split_covers_all(self):
        """All IDs are in either train or test."""
        from evaluation_service import StratifiedSplitter

        s = StratifiedSplitter()
        ids = [f"id-{i}" for i in range(100)]
        manifest = s.split(ids)
        all_ids = set(manifest.train_ids) | set(manifest.test_ids)
        self.assertEqual(all_ids, set(ids))

    def test_deterministic_with_seed(self):
        """Same seed produces same split."""
        from evaluation_service import StratifiedSplitter

        s1 = StratifiedSplitter(seed=42)
        s2 = StratifiedSplitter(seed=42)
        ids = [f"id-{i}" for i in range(100)]
        m1 = s1.split(ids)
        m2 = s2.split(ids)
        self.assertEqual(m1.train_ids, m2.train_ids)
        self.assertEqual(m1.test_ids, m2.test_ids)

    def test_different_seed_different_split(self):
        """Different seeds produce different splits."""
        from evaluation_service import StratifiedSplitter

        s1 = StratifiedSplitter(seed=42)
        s2 = StratifiedSplitter(seed=99)
        ids = [f"id-{i}" for i in range(100)]
        m1 = s1.split(ids)
        m2 = s2.split(ids)
        self.assertNotEqual(m1.train_ids, m2.train_ids)

    def test_stratified_with_labels(self):
        """Stratified split preserves label proportions."""
        from evaluation_service import StratifiedSplitter

        s = StratifiedSplitter()
        ids = [f"id-{i}" for i in range(100)]
        labels = ["A"] * 70 + ["B"] * 30
        manifest = s.split(ids, labels=labels)
        test_labels = [labels[int(tid.split("-")[1])] for tid in manifest.test_ids]
        a_count = test_labels.count("A")
        b_count = test_labels.count("B")
        self.assertGreater(a_count, 0)
        self.assertGreater(b_count, 0)

    def test_small_dataset(self):
        """Works with very small datasets."""
        from evaluation_service import StratifiedSplitter

        s = StratifiedSplitter()
        ids = ["id-0", "id-1"]
        manifest = s.split(ids)
        total = len(manifest.train_ids) + len(manifest.test_ids)
        self.assertEqual(total, 2)

    def test_empty_dataset(self):
        """Empty dataset produces empty splits."""
        from evaluation_service import StratifiedSplitter

        s = StratifiedSplitter()
        manifest = s.split([])
        self.assertEqual(len(manifest.train_ids), 0)
        self.assertEqual(len(manifest.test_ids), 0)

    def test_custom_ratio(self):
        """Custom 80/20 split."""
        from evaluation_service import StratifiedSplitter

        s = StratifiedSplitter(train_ratio=0.8, test_ratio=0.2)
        ids = [f"id-{i}" for i in range(100)]
        manifest = s.split(ids)
        self.assertEqual(len(manifest.train_ids), 80)
        self.assertEqual(len(manifest.test_ids), 20)

    def test_manifest_seed(self):
        """Split manifest records the seed."""
        from evaluation_service import StratifiedSplitter

        s = StratifiedSplitter(seed=123)
        manifest = s.split(["id-0"])
        self.assertEqual(manifest.seed, 123)


class TestValidationSelector(unittest.TestCase):
    """Multi-candidate ranking and selection."""

    def test_rank_candidates(self):
        """rank_candidates sorts by score descending."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig
        ValidationSelector = import_module(
            "evaluation_service.validation_selector"
        ).ValidationSelector

        es = EvaluationService(EvaluationServiceConfig())
        vs = ValidationSelector(es)
        c1 = ExecutionResult(run_id="r1", exit_code=1, logs_ref="l", artifacts_ref="a")
        c2 = ExecutionResult(run_id="r2", exit_code=0, logs_ref="l", artifacts_ref="a")
        ranked = vs.rank_candidates([c1, c2])
        self.assertEqual(ranked[0][0].run_id, "r2")

    def test_select_best(self):
        """select_best returns highest scorer."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig
        ValidationSelector = import_module(
            "evaluation_service.validation_selector"
        ).ValidationSelector

        es = EvaluationService(EvaluationServiceConfig())
        vs = ValidationSelector(es)
        c1 = ExecutionResult(run_id="r1", exit_code=1, logs_ref="l", artifacts_ref="a")
        c2 = ExecutionResult(run_id="r2", exit_code=0, logs_ref="l", artifacts_ref="a")
        best, score = vs.select_best([c1, c2])
        self.assertEqual(best.run_id, "r2")
        self.assertGreater(score.value, 0.0)

    def test_rank_single_candidate(self):
        """rank_candidates works with one candidate."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig
        ValidationSelector = import_module(
            "evaluation_service.validation_selector"
        ).ValidationSelector

        es = EvaluationService(EvaluationServiceConfig())
        vs = ValidationSelector(es)
        c = ExecutionResult(run_id="r1", exit_code=0, logs_ref="l", artifacts_ref="a")
        ranked = vs.rank_candidates([c])
        self.assertEqual(len(ranked), 1)

    def test_rank_empty_list(self):
        """rank_candidates with empty list returns empty."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig
        ValidationSelector = import_module(
            "evaluation_service.validation_selector"
        ).ValidationSelector

        es = EvaluationService(EvaluationServiceConfig())
        vs = ValidationSelector(es)
        ranked = vs.rank_candidates([])
        self.assertEqual(len(ranked), 0)


class TestAggregateBranchScores(unittest.TestCase):
    """aggregate_branch_scores returns weighted average."""

    def test_aggregate_average(self):
        """Aggregation returns average of scores."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        s1 = Score(score_id="s1", value=0.8, metric_name="m")
        s2 = Score(score_id="s2", value=0.6, metric_name="m")
        agg = es.aggregate_branch_scores([s1, s2])
        self.assertAlmostEqual(agg.value, 0.7)

    def test_aggregate_single(self):
        """Single score returns that score's value."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        s = Score(score_id="s1", value=0.8, metric_name="m")
        agg = es.aggregate_branch_scores([s])
        self.assertAlmostEqual(agg.value, 0.8)

    def test_aggregate_empty(self):
        """Empty list returns zero score."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        agg = es.aggregate_branch_scores([])
        self.assertAlmostEqual(agg.value, 0.0)


class TestGetLeaderboard(unittest.TestCase):
    """Leaderboard tracking."""

    def test_leaderboard_empty(self):
        """New task has empty leaderboard."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        lb = es.get_leaderboard("task-1")
        self.assertEqual(lb, {})

    def test_leaderboard_after_eval(self):
        """Leaderboard tracks evaluated runs."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        er = ExecutionResult(
            run_id="r1",
            exit_code=0,
            logs_ref="l",
            artifacts_ref="a",
            duration_sec=5.0,
        )
        es.evaluate_run(er)
        lb = es.get_leaderboard("default")
        self.assertIsInstance(lb, dict)
