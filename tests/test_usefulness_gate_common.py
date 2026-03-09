from __future__ import annotations

import json
from pathlib import Path

from data_models import ExecutionResult
from plugins.contracts import CommonUsefulnessGate, ScenarioContext
from scenarios.data_science.plugin import build_data_science_v1_bundle


def _scenario_context() -> ScenarioContext:
    return ScenarioContext(
        run_id="run-gate",
        scenario_name="data_science",
        input_payload={"task_summary": "gate test", "loop_index": 0},
        task_summary="gate test",
    )


def test_common_gate_rejects_template_only_output(tmp_path: Path) -> None:
    artifact = tmp_path / "metrics.json"
    artifact.write_text("TODO: fill in metrics", encoding="utf-8")
    result = ExecutionResult(
        run_id="run-template",
        exit_code=0,
        logs_ref="completed",
        artifacts_ref=json.dumps([str(artifact)]),
    )

    gate = CommonUsefulnessGate()
    outcome, signal = gate.evaluate(result, _scenario_context())

    assert not outcome.usefulness_eligible
    assert signal.stage == "semantic"
    assert signal.reason == "template-only output"


def test_common_gate_rejects_missing_key_field_output(tmp_path: Path) -> None:
    artifact = tmp_path / "metrics.json"
    artifact.write_text(json.dumps({"status": "ok"}), encoding="utf-8")
    result = ExecutionResult(
        run_id="run-missing-key",
        exit_code=0,
        logs_ref="{\"status\":\"ok\"}",
        artifacts_ref=json.dumps([str(artifact)]),
    )

    gate = CommonUsefulnessGate()
    outcome, signal = gate.evaluate(result, _scenario_context())

    assert not outcome.usefulness_eligible
    assert signal.stage == "utility"
    assert signal.reason == "missing key field"


def test_common_gate_rejects_contradictory_status_output(tmp_path: Path) -> None:
    artifact = tmp_path / "metrics.json"
    artifact.write_text(json.dumps({"status": "ok failed", "row_count": 12}), encoding="utf-8")
    result = ExecutionResult(
        run_id="run-contradictory",
        exit_code=0,
        logs_ref="run complete",
        artifacts_ref=json.dumps([str(artifact)]),
    )

    gate = CommonUsefulnessGate()
    outcome, signal = gate.evaluate(result, _scenario_context())

    assert not outcome.usefulness_eligible
    assert signal.stage == "utility"
    assert signal.reason == "contradictory status"


def test_scene_validator_layers_on_common_gate(tmp_path: Path) -> None:
    artifact = tmp_path / "metrics.json"
    artifact.write_text(json.dumps({"status": "ok", "row_count": "n/a"}), encoding="utf-8")
    result = ExecutionResult(
        run_id="run-scene-layer",
        exit_code=0,
        logs_ref="{\"status\":\"ok\",\"row_count\":\"n/a\"}",
        artifacts_ref=json.dumps([str(artifact)]),
    )

    bundle = build_data_science_v1_bundle()
    gate = CommonUsefulnessGate()
    outcome, signal = gate.evaluate(
        result,
        _scenario_context(),
        scene_validator=bundle.scene_usefulness_validator,
    )

    assert not outcome.usefulness_eligible
    assert signal.stage == "utility"
    assert signal.reason == "scene validator rejected: row_count must be integer"


def test_scene_validator_rejects_row_count_only_payload(tmp_path: Path) -> None:
    artifact = tmp_path / "metrics.json"
    artifact.write_text(json.dumps({"status": "ok", "row_count": 12}), encoding="utf-8")
    result = ExecutionResult(
        run_id="run-row-count-only",
        exit_code=0,
        logs_ref="Analysis summary says this run is strong.",
        artifacts_ref=json.dumps([str(artifact)]),
    )

    bundle = build_data_science_v1_bundle()
    gate = CommonUsefulnessGate()
    outcome, signal = gate.evaluate(
        result,
        _scenario_context(),
        scene_validator=bundle.scene_usefulness_validator,
    )

    assert not outcome.usefulness_eligible
    assert signal.stage == "utility"
    assert signal.reason == "scene validator rejected: row-count-only payload"


def test_scene_validator_rejects_template_only_metric_value(tmp_path: Path) -> None:
    artifact = tmp_path / "metrics.json"
    artifact.write_text(
        json.dumps({"status": "ok", "row_count": 12, "column_count": "placeholder"}),
        encoding="utf-8",
    )
    result = ExecutionResult(
        run_id="run-template-metric",
        exit_code=0,
        logs_ref="{\"status\":\"ok\",\"row_count\":12,\"column_count\":\"placeholder\"}",
        artifacts_ref=json.dumps([str(artifact)]),
    )

    bundle = build_data_science_v1_bundle()
    gate = CommonUsefulnessGate()
    outcome, signal = gate.evaluate(
        result,
        _scenario_context(),
        scene_validator=bundle.scene_usefulness_validator,
    )

    assert not outcome.usefulness_eligible
    assert signal.stage == "semantic"
    assert signal.reason == "template-only output"


def test_common_gate_rejects_malformed_required_artifact_status() -> None:
    result = ExecutionResult(
        run_id="run-malformed-artifact",
        exit_code=0,
        logs_ref='{"status":"ok","row_count":12,"metric":0.9}',
        artifacts_ref="not-a-json-manifest",
    )

    gate = CommonUsefulnessGate()
    outcome, signal = gate.evaluate(result, _scenario_context())

    assert not outcome.usefulness_eligible
    assert outcome.artifact_status.value == "MALFORMED_REQUIRED"
    assert signal.stage == "semantic"
    assert signal.reason == "artifact verification failed: MALFORMED_REQUIRED"
