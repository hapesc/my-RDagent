from __future__ import annotations

import importlib.util
import json
import os
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
build_default_langsmith_backend_from_env = _MODULE.build_default_langsmith_backend_from_env
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

    def test_main_reads_compare_baseline_and_persists_comparison(self) -> None:
        def fake_runner(**kwargs):
            return BenchmarkRunResult(
                run_id="run-cli-2",
                profile="smoke",
                scenario="data_science",
                case_results=[],
                summary={"total_cases": 0},
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            baseline_path.write_text(json.dumps({"summary": {"total_cases": 3}}), encoding="utf-8")

            exit_code = main(
                [
                    "--profile",
                    "smoke",
                    "--scenario",
                    "data_science",
                    "--output-dir",
                    tmpdir,
                    "--compare-baseline",
                    str(baseline_path),
                ],
                benchmark_runner=fake_runner,
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads((Path(tmpdir) / "benchmark-result.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["baseline"]["summary"]["total_cases"], 3)
            self.assertEqual(payload["baseline_comparison"]["delta_total_cases"], -3)

    def test_main_uploads_results_when_backend_is_provided(self) -> None:
        calls = {"upload": 0}

        class FakeBackend:
            def publish_run(self, result, **kwargs):
                _ = result
                calls["upload"] += 1
                return {"experiment": {"experiment_id": "exp-1"}, **kwargs}

        def fake_runner(**kwargs):
            return BenchmarkRunResult(
                run_id="run-cli-3",
                profile="smoke",
                scenario="data_science",
                case_results=[],
                summary={"total_cases": 0},
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            exit_code = main(
                [
                    "--profile",
                    "smoke",
                    "--scenario",
                    "data_science",
                    "--output-dir",
                    tmpdir,
                    "--upload-results",
                ],
                benchmark_runner=fake_runner,
                langsmith_backend=FakeBackend(),
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(calls["upload"], 1)

    def test_main_uses_default_langsmith_backend_when_tracing_enabled(self) -> None:
        def fake_runner(**kwargs):
            return BenchmarkRunResult(
                run_id="run-cli-4",
                profile="smoke",
                scenario="data_science",
                case_results=[],
                summary={"total_cases": 0},
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            env = dict(os.environ)
            env["LANGSMITH_TRACING"] = "true"
            old = dict(os.environ)
            os.environ.update(env)
            try:
                exit_code = main(
                    ["--profile", "smoke", "--scenario", "data_science", "--output-dir", tmpdir, "--upload-results"],
                    benchmark_runner=fake_runner,
                    langsmith_backend=_MODULE.LangSmithBackend(client=_MODULE.NullLangSmithExperimentClient()),
                )
            finally:
                os.environ.clear()
                os.environ.update(old)

            self.assertEqual(exit_code, 0)
            payload = json.loads((Path(tmpdir) / "benchmark-result.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["upload"]["experiment"]["experiment_id"], "local-smoke-data_science")

    def test_default_langsmith_backend_is_disabled_without_api_key(self) -> None:
        old = dict(os.environ)
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ.pop("LANGSMITH_API_KEY", None)
        try:
            backend = build_default_langsmith_backend_from_env()
        finally:
            os.environ.clear()
            os.environ.update(old)

        self.assertIsNone(backend)


if __name__ == "__main__":
    unittest.main()
