"""Standalone CLI for the LangSmith benchmark stack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarking.reporting import run_result_to_json_dict, summarize_run_markdown
from benchmarking.runner import run_benchmark


def _default_runtime_target(task) -> dict:
    return {
        "status": "COMPLETED",
        "outputs": {"task_id": task.task_id},
        "artifact_refs": {},
        "timing": {},
        "runtime": {},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_langsmith_benchmark")
    parser.add_argument("--profile", required=True, choices=("smoke", "daily", "full"))
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--compare-baseline", default=None)
    parser.add_argument("--upload-results", action="store_true")
    return parser


def run_cli(
    args: argparse.Namespace,
    *,
    benchmark_runner=run_benchmark,
    json_renderer=run_result_to_json_dict,
    markdown_renderer=summarize_run_markdown,
) -> int:
    result = benchmark_runner(
        run_id=f"benchmark-{args.profile}",
        profile_name=args.profile,
        scenario=args.scenario,
        runtime_target=_default_runtime_target,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_payload = json_renderer(result)
    markdown_summary = markdown_renderer(result)
    (output_dir / "benchmark-result.json").write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "benchmark-summary.md").write_text(markdown_summary, encoding="utf-8")
    return 0


def main(
    argv: list[str] | None = None,
    *,
    benchmark_runner=run_benchmark,
    json_renderer=run_result_to_json_dict,
    markdown_renderer=summarize_run_markdown,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_cli(
        args,
        benchmark_runner=benchmark_runner,
        json_renderer=json_renderer,
        markdown_renderer=markdown_renderer,
    )


if __name__ == "__main__":
    raise SystemExit(main())
