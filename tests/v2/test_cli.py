from __future__ import annotations

import json
import importlib

cli_module = importlib.import_module("v2.cli")
build_parser = cli_module.build_parser
main = cli_module.main


def test_build_parser_returns_parser():
    parser = build_parser()
    assert parser is not None


def test_main_run_exits_zero(capsys):
    exit_code = main(["run", "--scenario", "data_science", "--task-summary", "test", "--max-loops", "1"])
    assert exit_code == 0


def test_main_run_prints_json_with_run_id(capsys):
    main(["run", "--scenario", "data_science", "--task-summary", "test"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "run_id" in data
    assert data["command"] == "run"


def test_main_run_prints_json_with_status(capsys):
    main(["run", "--scenario", "data_science", "--task-summary", "test"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "status" in data


def test_main_help_exits_nonzero():
    exit_code = main([])
    assert exit_code != 0
