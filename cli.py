"""Quick-start CLI for Agentic R&D Platform."""

from __future__ import annotations

import argparse
import logging
import sys

from app.runtime import build_runtime, build_run_service

logger = logging.getLogger(__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Agentic R&D Platform - Quick Start")
    parser.add_argument("--scenario", default="data_science", help="Scenario plugin name (default: data_science)")
    parser.add_argument("--task", required=True, help="Task description string")
    parser.add_argument("--max-steps", type=int, default=5, help="Maximum iteration steps (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Initialize only, do not run")
    args = parser.parse_args(argv)
    
    runtime = build_runtime()
    
    logger.info("scenario: %s", args.scenario)
    logger.info("llm_provider: %s", runtime.config.llm_provider)
    logger.info("costeer_max_rounds: %s", runtime.config.costeer_max_rounds)
    logger.info("task: %s", args.task)
    logger.info("max_steps: %s", args.max_steps)
    
    if args.dry_run:
        logger.info("dry-run: exiting without starting loop")
        return 0
    
    run_service = build_run_service(runtime, args.scenario)
    session = run_service.create_run(task_summary=args.task, scenario=args.scenario)
    run_service.start_run(run_id=session.run_id, task_summary=args.task, loops_per_call=args.max_steps)
    logger.info("run completed: %s", session.run_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
