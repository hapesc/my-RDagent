from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import scripts.run_quant_e2e as script


def _sample_ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2024-01-02",
                "stock_id": "AAPL",
                "open": 185.64,
                "high": 188.44,
                "low": 183.89,
                "close": 185.64,
                "volume": 82488700,
            },
            {
                "date": "2024-01-02",
                "stock_id": "MSFT",
                "open": 370.87,
                "high": 373.26,
                "low": 366.78,
                "close": 370.87,
                "volume": 25258600,
            },
        ]
    )


def _write_minimal_config(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(
        "\n".join(
            [
                "llm_provider: mock",
                "allow_local_execution: true",
                "run_defaults:",
                "  scenario: quant",
                "  stop_conditions:",
                "    max_loops: 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


@patch("scripts.run_quant_e2e.subprocess.run")
@patch("scripts.run_quant_e2e.YFinanceDataProvider")
def test_quant_e2e_script_invokes_unified_cli(mock_provider_cls, mock_subprocess_run, tmp_path, monkeypatch) -> None:
    mock_provider = mock_provider_cls.return_value
    mock_provider.load.return_value = _sample_ohlcv()
    mock_subprocess_run.return_value = subprocess.CompletedProcess(args=["python"], returncode=0)
    monkeypatch.setattr(script, "PROJECT_ROOT", tmp_path)
    _write_minimal_config(tmp_path)

    script.main(
        [
            "--tickers",
            "AAPL,MSFT",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
            "--task-summary",
            "mine factor from yfinance",
            "--max-loops",
            "2",
        ]
    )

    assert mock_subprocess_run.call_count == 1
    cmd = mock_subprocess_run.call_args.args[0]
    assert cmd[0].endswith("python3.11") or cmd[0].endswith("python") or "python" in cmd[0]
    assert cmd[1].endswith("agentrd_cli.py")
    assert cmd[2:5] == ["run", "--config", str(tmp_path / "config.yaml")]
    assert "--scenario" in cmd and cmd[cmd.index("--scenario") + 1] == "quant"
    assert "--data-source" in cmd
    assert "--task-summary" in cmd and cmd[cmd.index("--task-summary") + 1] == "mine factor from yfinance"
    assert "--max-loops" in cmd and cmd[cmd.index("--max-loops") + 1] == "2"


@patch("scripts.run_quant_e2e.subprocess.run")
@patch("scripts.run_quant_e2e.YFinanceDataProvider")
def test_quant_e2e_script_deletes_temp_csv_on_success(
    mock_provider_cls,
    mock_subprocess_run,
    tmp_path,
    monkeypatch,
) -> None:
    mock_provider = mock_provider_cls.return_value
    mock_provider.load.return_value = _sample_ohlcv()
    mock_subprocess_run.return_value = subprocess.CompletedProcess(args=["python"], returncode=0)
    monkeypatch.setattr(script, "PROJECT_ROOT", tmp_path)
    _write_minimal_config(tmp_path)

    captured: dict[str, Path] = {}

    def _capture_run(cmd, check=False):  # noqa: ANN001
        captured["csv"] = Path(cmd[cmd.index("--data-source") + 1])
        assert captured["csv"].exists()
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    mock_subprocess_run.side_effect = _capture_run

    script.main(["--tickers", "AAPL,MSFT"])

    assert "csv" in captured
    assert not captured["csv"].exists()


@patch("scripts.run_quant_e2e.subprocess.run")
@patch("scripts.run_quant_e2e.YFinanceDataProvider")
def test_quant_e2e_script_deletes_temp_csv_on_failure(
    mock_provider_cls,
    mock_subprocess_run,
    tmp_path,
    monkeypatch,
) -> None:
    mock_provider = mock_provider_cls.return_value
    mock_provider.load.return_value = _sample_ohlcv()
    monkeypatch.setattr(script, "PROJECT_ROOT", tmp_path)
    _write_minimal_config(tmp_path)

    captured: dict[str, Path] = {}

    def _capture_run(cmd, check=False):  # noqa: ANN001
        captured["csv"] = Path(cmd[cmd.index("--data-source") + 1])
        assert captured["csv"].exists()
        return subprocess.CompletedProcess(args=cmd, returncode=4)

    mock_subprocess_run.side_effect = _capture_run

    with pytest.raises(SystemExit) as exc:
        script.main(["--tickers", "AAPL,MSFT"])

    assert exc.value.code == 4
    assert "csv" in captured
    assert not captured["csv"].exists()
