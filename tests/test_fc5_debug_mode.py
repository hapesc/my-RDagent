"""Tests for FC-5 debug mode — config, duration propagation, multi-stage evaluation."""

import unittest

from data_models import ExecutionResult


class TestDebugModeConfig(unittest.TestCase):
    """AppConfig debug mode fields."""

    def test_config_defaults(self):
        """Default config has debug_mode=False."""
        from app.config import load_config

        c = load_config({})
        self.assertFalse(c.debug_mode)
        self.assertAlmostEqual(c.debug_sample_fraction, 0.1)
        self.assertEqual(c.debug_max_epochs, 5)

    def test_config_from_env(self):
        """Config loads debug settings from env vars."""
        from app.config import load_config

        c = load_config(
            {
                "RD_AGENT_DEBUG_MODE": "true",
                "RD_AGENT_DEBUG_SAMPLE_FRACTION": "0.2",
                "RD_AGENT_DEBUG_MAX_EPOCHS": "3",
            }
        )
        self.assertTrue(c.debug_mode)
        self.assertAlmostEqual(c.debug_sample_fraction, 0.2)
        self.assertEqual(c.debug_max_epochs, 3)

    def test_config_debug_mode_false(self):
        """Config with debug_mode=false."""
        from app.config import load_config

        c = load_config({"RD_AGENT_DEBUG_MODE": "false"})
        self.assertFalse(c.debug_mode)


class TestMultiStageEvaluation(unittest.TestCase):
    """EvaluationService multi-stage evaluation."""

    def test_evaluate_run_success(self):
        """exit_code=0 produces positive score."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        er = ExecutionResult(
            run_id="r1",
            exit_code=0,
            logs_ref="log",
            artifacts_ref="art",
            duration_sec=5.0,
            timed_out=False,
        )
        result = es.evaluate_run(er)
        self.assertGreater(result.score.value, 0.0)
        self.assertIn("stages", result.score.details)

    def test_evaluate_run_failure(self):
        """exit_code=1 scores lower than exit_code=0."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        good = ExecutionResult(
            run_id="r1",
            exit_code=0,
            logs_ref="log",
            artifacts_ref="art",
            duration_sec=5.0,
        )
        bad = ExecutionResult(
            run_id="r2",
            exit_code=1,
            logs_ref="log",
            artifacts_ref="art",
            duration_sec=5.0,
        )
        good_result = es.evaluate_run(good)
        bad_result = es.evaluate_run(bad)
        self.assertGreater(good_result.score.value, bad_result.score.value)

    def test_evaluate_run_stage_details(self):
        """Score details contain stage results."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        er = ExecutionResult(
            run_id="r1",
            exit_code=0,
            logs_ref="log",
            artifacts_ref="art",
            duration_sec=5.0,
        )
        result = es.evaluate_run(er)
        stages = result.score.details.get("stages", "")
        self.assertIn("execution", stages)

    def test_evaluate_run_no_artifacts(self):
        """Empty artifacts_ref scores lower on alignment stage."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        with_art = ExecutionResult(
            run_id="r1",
            exit_code=0,
            logs_ref="log",
            artifacts_ref="art",
        )
        no_art = ExecutionResult(
            run_id="r2",
            exit_code=0,
            logs_ref="log",
            artifacts_ref="",
        )
        with_score = es.evaluate_run(with_art).score.value
        no_score = es.evaluate_run(no_art).score.value
        self.assertGreaterEqual(with_score, no_score)

    def test_evaluate_run_timed_out(self):
        """Timed-out execution scores lower."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        normal = ExecutionResult(
            run_id="r1",
            exit_code=0,
            logs_ref="log",
            artifacts_ref="art",
            duration_sec=5.0,
            timed_out=False,
        )
        timed_out = ExecutionResult(
            run_id="r2",
            exit_code=0,
            logs_ref="log",
            artifacts_ref="art",
            duration_sec=300.0,
            timed_out=True,
        )
        normal_score = es.evaluate_run(normal).score.value
        timeout_score = es.evaluate_run(timed_out).score.value
        self.assertGreater(normal_score, timeout_score)

    def test_evaluate_run_score_range(self):
        """Score value is in [0, 1]."""
        from evaluation_service.service import EvaluationService, EvaluationServiceConfig

        es = EvaluationService(EvaluationServiceConfig())
        for exit_code in [0, 1]:
            for art in ["art", ""]:
                er = ExecutionResult(
                    run_id="r",
                    exit_code=exit_code,
                    logs_ref="log",
                    artifacts_ref=art,
                    duration_sec=5.0,
                )
                score = es.evaluate_run(er).score.value
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)


class TestEvaluationServiceConfig(unittest.TestCase):
    """EvaluationServiceConfig backward compatibility."""

    def test_default_config(self):
        """Default config still works."""
        from evaluation_service.service import EvaluationServiceConfig

        c = EvaluationServiceConfig()
        self.assertEqual(c.metric_name, "placeholder_metric")
