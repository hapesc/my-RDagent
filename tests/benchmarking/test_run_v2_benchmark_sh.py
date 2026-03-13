from __future__ import annotations

import os
import subprocess
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_v2_benchmark.sh"


def test_run_v2_benchmark_script_help() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--profile" in result.stdout
    assert "--output-root" in result.stdout


def test_run_v2_benchmark_script_rejects_mock_provider_by_default(tmp_path) -> None:
    env = dict(os.environ)
    env["RD_AGENT_LLM_PROVIDER"] = "mock"
    env["RD_AGENT_LLM_MODEL"] = "mock-model"

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--output-root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode != 0
    assert "real provider" in (result.stderr or result.stdout).lower()
