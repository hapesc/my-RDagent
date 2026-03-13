from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from benchmarking.result_schema import BenchmarkRunResult


_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "run_langsmith_benchmark.py"
)
_SPEC = importlib.util.spec_from_file_location("run_langsmith_benchmark", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

build_parser = _MODULE.build_parser
main = _MODULE.main


class BenchmarkCliTests(unittest.TestCase):
    def test_cli_accepts_required_benchmark_arguments(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--profile",
                "smoke",
                "--scenario",
                "data_science",
                "--output-dir",
                "/tmp/out",
                "--compare-baseline",
                "/tmp/baseline.json",
                "--upload-results",
            ]
        )

        self.assertEqual(args.profile, "smoke")
        self.assertEqual(args.scenario, "data_science")
        self.assertEqual(args.output_dir, "/tmp/out")
        self.assertEqual(args.compare_baseline, "/tmp/baseline.json")
        self.assertTrue(args.upload_results)

    def test_cli_defaults_upload_results_to_false(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--profile", "smoke", "--output-dir", "/tmp/out"])

        self.assertFalse(args.upload_results)

    def test_main_runs_runner_and_writes_outputs(self) -> None:
        calls = {"runner": 0}

        def fake_runner(**kwargs):
            calls["runner"] += 1
            self.assertEqual(kwargs["profile_name"], "smoke")
            return BenchmarkRunResult(
                run_id="run-cli-1",
                profile="smoke",
                scenario="data_science",
                case_results=[],
                summary={"total_cases": 0},
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            exit_code = main(
                ["--profile", "smoke", "--scenario", "data_science", "--output-dir", tmpdir],
                benchmark_runner=fake_runner,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(calls["runner"], 1)
            self.assertTrue((Path(tmpdir) / "benchmark-result.json").exists())
            self.assertTrue((Path(tmpdir) / "benchmark-summary.md").exists())


if __name__ == "__main__":
    unittest.main()
