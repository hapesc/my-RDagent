"""Standalone CLI for the LangSmith benchmark stack."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from benchmarking.langsmith_backend import (
    HostedLangSmithExperimentClient,
    LangSmithBackend,
    NullLangSmithExperimentClient,
)
from benchmarking.profiles import get_profile
from benchmarking.reporting import run_result_to_json_dict, summarize_run_markdown
from benchmarking.runner import run_benchmark
from v2.runtime import build_v2_runtime


def _make_v2_runtime_target(*, profile_name: str, scenario: str | None):
    profile = get_profile(profile_name)
    ctx = build_v2_runtime(
        {
            "llm_provider": os.environ.get("RD_AGENT_LLM_PROVIDER", "mock"),
            "llm_model": os.environ.get("RD_AGENT_LLM_MODEL", "gpt-4o-mini"),
            "llm_api_key": os.environ.get("RD_AGENT_LLM_API_KEY"),
            "llm_base_url": os.environ.get("RD_AGENT_LLM_BASE_URL"),
            "judge_model": os.environ.get("RD_AGENT_JUDGE_MODEL"),
            "max_loops": profile.max_loops,
            "artifact_root": os.environ.get("AGENTRD_ARTIFACT_ROOT", "/tmp/v2-benchmark-artifacts"),
        }
    )

    def runtime_target(task) -> dict:
        run_id = ctx.run_service.create_run(
            {
                "scenario": scenario or task.scenario,
                "task_summary": task.task_summary,
                "max_loops": profile.max_loops,
            }
        )
        ctx.run_service.start_run(run_id)
        payload = ctx.run_service.get_run_payload(run_id) or {}
        return {
            "status": payload.get("status", "UNKNOWN"),
            "outputs": dict(payload.get("final_state", {}).get("state", {})),
            "artifact_refs": dict(payload.get("artifacts", {})),
            "timing": {"loop_iteration": payload.get("loop_iteration")},
            "runtime": dict(payload.get("runtime", {})),
        }

    return runtime_target


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
    langsmith_backend: Any | None = None,
) -> int:
    result = benchmark_runner(
        run_id=f"benchmark-{args.profile}",
        profile_name=args.profile,
        scenario=args.scenario,
        runtime_target=_make_v2_runtime_target(profile_name=args.profile, scenario=args.scenario),
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_payload = json_renderer(result)
    if args.compare_baseline:
        baseline = json.loads(Path(args.compare_baseline).read_text(encoding="utf-8"))
        current_total = int(json_payload.get("summary", {}).get("total_cases", 0))
        baseline_total = int(baseline.get("summary", {}).get("total_cases", 0))
        json_payload["baseline"] = baseline
        json_payload["baseline_comparison"] = {
            "current_total_cases": current_total,
            "baseline_total_cases": baseline_total,
            "delta_total_cases": current_total - baseline_total,
        }
    if args.upload_results and langsmith_backend is not None:
        json_payload["upload"] = langsmith_backend.publish_run(
            result,
            dataset_name=f"rdagent-{args.profile}",
            experiment_name=f"{args.profile}-{args.scenario or 'all'}",
            case_evaluators=("rules", "scenario", "judge"),
            summary_evaluators=("aggregate_pass_rate",),
        )
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
    langsmith_backend: Any | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_cli(
        args,
        benchmark_runner=benchmark_runner,
        json_renderer=json_renderer,
        markdown_renderer=markdown_renderer,
        langsmith_backend=langsmith_backend,
    )


def build_default_langsmith_backend_from_env() -> Any | None:
    tracing_enabled = os.environ.get("LANGSMITH_TRACING", "").strip().lower() in {"1", "true", "yes", "on"}
    api_key = os.environ.get("LANGSMITH_API_KEY")
    if not tracing_enabled:
        return None
    if not api_key:
        os.environ["LANGSMITH_TRACING"] = "false"
        return None
    try:
        from langsmith import Client
    except Exception:
        return LangSmithBackend(client=NullLangSmithExperimentClient())

    return LangSmithBackend(client=HostedLangSmithExperimentClient(Client()))


if __name__ == "__main__":
    backend = build_default_langsmith_backend_from_env()
    raise SystemExit(main(langsmith_backend=backend))
