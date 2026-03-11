"""Tests for correction exception hierarchy."""

from __future__ import annotations

import unittest


class TestExceptionHierarchy(unittest.TestCase):
    def test_coder_error_is_skip_iteration_error(self) -> None:
        from core.correction.exceptions import CoderError, SkipIterationError

        with self.assertRaises(SkipIterationError):
            raise CoderError("compile failed")

    def test_runner_error_is_skip_iteration_error(self) -> None:
        from core.correction.exceptions import RunnerError, SkipIterationError

        with self.assertRaises(SkipIterationError):
            raise RunnerError("execution timeout")

    def test_coder_error_preserves_message(self) -> None:
        from core.correction.exceptions import CoderError

        err = CoderError("missing import numpy")
        self.assertEqual(str(err), "missing import numpy")

    def test_runner_error_preserves_message(self) -> None:
        from core.correction.exceptions import RunnerError

        err = RunnerError("exit code 1")
        self.assertEqual(str(err), "exit code 1")

    def test_skip_iteration_error_not_caught_by_runtime_error(self) -> None:
        from core.correction.exceptions import SkipIterationError

        with self.assertRaises(SkipIterationError):
            try:
                raise SkipIterationError("test")
            except RuntimeError:
                self.fail("SkipIterationError should NOT be a RuntimeError")

    def test_coder_error_caused_by_timeout_default_false(self) -> None:
        from core.correction.exceptions import CoderError

        err = CoderError("failed")
        self.assertFalse(err.caused_by_timeout)

    def test_coder_error_caused_by_timeout_explicit(self) -> None:
        from core.correction.exceptions import CoderError

        err = CoderError("timeout", caused_by_timeout=True)
        self.assertTrue(err.caused_by_timeout)


if __name__ == "__main__":
    unittest.main()
