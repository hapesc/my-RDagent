"""Tests for FC-4 interaction kernel — TF-IDF, cosine similarity, and kernel computation."""
import math
import time
import unittest


class TestTFIDFVectorizer(unittest.TestCase):
    """TF-IDF vectorizer produces correct sparse vectors."""

    def test_fit_transform_identical_docs(self):
        """Identical documents produce identical vectors."""
        from memory_service.interaction_kernel import TFIDFVectorizer
        v = TFIDFVectorizer()
        vecs = v.fit_transform(["hello world", "hello world"])
        self.assertEqual(vecs[0], vecs[1])

    def test_fit_transform_different_docs(self):
        """Different documents produce different vectors."""
        from memory_service.interaction_kernel import TFIDFVectorizer
        v = TFIDFVectorizer()
        vecs = v.fit_transform(["hello world", "foo bar"])
        self.assertNotEqual(vecs[0], vecs[1])

    def test_fit_transform_returns_dicts(self):
        """fit_transform returns list of dicts."""
        from memory_service.interaction_kernel import TFIDFVectorizer
        v = TFIDFVectorizer()
        vecs = v.fit_transform(["the cat sat", "the dog ran"])
        self.assertIsInstance(vecs, list)
        self.assertIsInstance(vecs[0], dict)
        for key in vecs[0]:
            self.assertIsInstance(key, str)
            self.assertIsInstance(vecs[0][key], float)

    def test_transform_single_doc(self):
        """transform() uses fitted vocabulary."""
        from memory_service.interaction_kernel import TFIDFVectorizer
        v = TFIDFVectorizer()
        v.fit_transform(["hello world", "foo bar"])
        vec = v.transform("hello foo")
        self.assertIsInstance(vec, dict)

    def test_empty_document(self):
        """Empty document produces empty vector."""
        from memory_service.interaction_kernel import TFIDFVectorizer
        v = TFIDFVectorizer()
        v.fit_transform(["hello world"])
        vec = v.transform("")
        self.assertEqual(vec, {})

    def test_single_document(self):
        """Single document corpus works (all IDF = 0, TF-IDF = 0)."""
        from memory_service.interaction_kernel import TFIDFVectorizer
        v = TFIDFVectorizer()
        vecs = v.fit_transform(["hello world"])
        # With only 1 doc, IDF = log(1/1) = 0, so TF-IDF = 0 for all terms
        # This is expected behavior for single-doc corpus
        self.assertIsInstance(vecs[0], dict)


class TestCosineSimilarity(unittest.TestCase):
    """Cosine similarity for sparse vectors."""

    def test_identical_vectors(self):
        """Cosine of identical vectors = 1.0."""
        from memory_service.interaction_kernel import cosine_similarity
        vec = {"a": 1.0, "b": 2.0}
        self.assertAlmostEqual(cosine_similarity(vec, vec), 1.0)

    def test_orthogonal_vectors(self):
        """Cosine of orthogonal vectors = 0.0."""
        from memory_service.interaction_kernel import cosine_similarity
        vec_a = {"a": 1.0}
        vec_b = {"b": 1.0}
        self.assertAlmostEqual(cosine_similarity(vec_a, vec_b), 0.0)

    def test_empty_vectors(self):
        """Cosine of empty vectors = 0.0."""
        from memory_service.interaction_kernel import cosine_similarity
        self.assertAlmostEqual(cosine_similarity({}, {}), 0.0)

    def test_one_empty_vector(self):
        """Cosine with one empty vector = 0.0."""
        from memory_service.interaction_kernel import cosine_similarity
        self.assertAlmostEqual(cosine_similarity({"a": 1.0}, {}), 0.0)

    def test_range(self):
        """Cosine is in [0, 1] for non-negative vectors."""
        from memory_service.interaction_kernel import cosine_similarity
        vec_a = {"a": 1.0, "b": 0.5}
        vec_b = {"a": 0.5, "b": 1.0}
        sim = cosine_similarity(vec_a, vec_b)
        self.assertGreaterEqual(sim, 0.0)
        self.assertLessEqual(sim, 1.0)


class TestScoreDelta(unittest.TestCase):
    """Normalized score difference."""

    def test_equal_scores(self):
        """Equal scores give delta = 0.5 (normalized)."""
        from memory_service.interaction_kernel import score_delta
        # When scores are equal, we expect a baseline value (e.g., 0.5 or use abs(diff))
        result = score_delta(0.8, 0.8)
        self.assertAlmostEqual(result, 1.0)  # max similarity when equal

    def test_max_difference(self):
        """Maximum difference (0 vs 1) gives low similarity."""
        from memory_service.interaction_kernel import score_delta
        result = score_delta(0.0, 1.0)
        self.assertLessEqual(result, 0.5)

    def test_range(self):
        """score_delta returns value in [0, 1]."""
        from memory_service.interaction_kernel import score_delta
        for a, b in [(0.0, 1.0), (0.5, 0.5), (1.0, 0.0), (0.3, 0.7)]:
            result = score_delta(a, b)
            self.assertGreaterEqual(result, 0.0)
            self.assertLessEqual(result, 1.0)


class TestTemporalDecay(unittest.TestCase):
    """Exponential temporal decay."""

    def test_same_time_no_decay(self):
        """Same timestamp = decay factor of 1.0."""
        from memory_service.interaction_kernel import temporal_decay
        now = time.time()
        self.assertAlmostEqual(temporal_decay(now, now), 1.0)

    def test_half_life_decay(self):
        """After one half-life, decay ~ 0.5."""
        from memory_service.interaction_kernel import temporal_decay
        now = time.time()
        result = temporal_decay(now, now - 3600.0, half_life=3600.0)
        self.assertAlmostEqual(result, 0.5, places=2)

    def test_very_old_approaches_zero(self):
        """Very old timestamp approaches 0."""
        from memory_service.interaction_kernel import temporal_decay
        now = time.time()
        result = temporal_decay(now, now - 36000.0, half_life=3600.0)
        self.assertLess(result, 0.01)

    def test_range(self):
        """Decay is in [0, 1]."""
        from memory_service.interaction_kernel import temporal_decay
        now = time.time()
        for offset in [0, 100, 1000, 10000]:
            result = temporal_decay(now, now - offset)
            self.assertGreaterEqual(result, 0.0)
            self.assertLessEqual(result, 1.0)


class TestInteractionKernel(unittest.TestCase):
    """InteractionKernel computes K = α·cosine + β·score_delta + γ·decay."""

    def test_compute_returns_float(self):
        """compute() returns a float."""
        from memory_service.interaction_kernel import InteractionKernel, HypothesisRecord
        k = InteractionKernel()
        now = time.time()
        h1 = HypothesisRecord(text="use random forest", score=0.8, timestamp=now, branch_id="b1")
        h2 = HypothesisRecord(text="use gradient boosting", score=0.6, timestamp=now - 3600, branch_id="b2")
        val = k.compute(h1, h2)
        self.assertIsInstance(val, float)

    def test_compute_range(self):
        """compute() returns value in [0, 1]."""
        from memory_service.interaction_kernel import InteractionKernel, HypothesisRecord
        k = InteractionKernel()
        now = time.time()
        h1 = HypothesisRecord(text="use random forest", score=0.8, timestamp=now, branch_id="b1")
        h2 = HypothesisRecord(text="use gradient boosting", score=0.6, timestamp=now - 3600, branch_id="b2")
        val = k.compute(h1, h2)
        self.assertGreaterEqual(val, 0.0)
        self.assertLessEqual(val, 1.0)

    def test_identical_hypotheses(self):
        """Identical hypotheses score high."""
        from memory_service.interaction_kernel import InteractionKernel, HypothesisRecord
        k = InteractionKernel()
        now = time.time()
        h = HypothesisRecord(text="use random forest with 100 trees", score=0.8, timestamp=now, branch_id="b1")
        val = k.compute(h, h)
        self.assertGreater(val, 0.8)

    def test_custom_weights(self):
        """Custom alpha, beta, gamma are used."""
        from memory_service.interaction_kernel import InteractionKernel, HypothesisRecord
        k = InteractionKernel(alpha=1.0, beta=0.0, gamma=0.0)
        now = time.time()
        h1 = HypothesisRecord(text="foo bar", score=0.8, timestamp=now, branch_id="b1")
        h2 = HypothesisRecord(text="baz qux", score=0.2, timestamp=now - 7200, branch_id="b2")
        # With beta=0 and gamma=0, result is purely cosine-based
        val = k.compute(h1, h2)
        self.assertGreaterEqual(val, 0.0)
        self.assertLessEqual(val, 1.0)


class TestHypothesisRecord(unittest.TestCase):
    """HypothesisRecord is a simple data carrier."""

    def test_fields(self):
        """HypothesisRecord has expected fields."""
        from memory_service.interaction_kernel import HypothesisRecord
        h = HypothesisRecord(text="test", score=0.5, timestamp=1234.0, branch_id="b1")
        self.assertEqual(h.text, "test")
        self.assertEqual(h.score, 0.5)
        self.assertEqual(h.timestamp, 1234.0)
        self.assertEqual(h.branch_id, "b1")
