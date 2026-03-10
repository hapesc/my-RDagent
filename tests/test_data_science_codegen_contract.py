from __future__ import annotations

import sys
import types
import importlib.util
from pathlib import Path
from typing import Any

from data_models import CodeArtifact, DebugConfig
from data_models import ExperimentNode, Proposal
from llm import CodeDraft
from plugins.contracts import ScenarioContext
from tests._llm_test_utils import make_mock_llm_adapter


if "pandas" not in sys.modules:
    fake_pandas = types.ModuleType("pandas")
    setattr(fake_pandas, "read_csv", lambda *args, **kwargs: [])
    sys.modules["pandas"] = fake_pandas


def _load_data_science_coder() -> Any:
    plugin_path = Path(__file__).resolve().parents[1] / "scenarios" / "data_science" / "plugin.py"
    module_name = "data_science_plugin_under_test"
    spec = importlib.util.spec_from_file_location(module_name, plugin_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.DataScienceCoder


def _llm_code() -> str:
    return (
        "import pandas as pd\n"
        "df = pd.read_csv(data_source)\n"
        "metrics = {'row_count': len(df)}\n"
        "import json\n"
        "with open('metrics.json', 'w') as f:\n"
        "    json.dump(metrics, f)\n"
        "print(metrics['row_count'])\n"
    )


def _build_inputs(tmp_path: Path) -> tuple[Any, ExperimentNode, Proposal, ScenarioContext, Path]:
    workspace = tmp_path / "workspace"
    data_source = tmp_path / "train.csv"
    data_source.write_text("id,x,y\n1,10,1\n2,11,0\n", encoding="utf-8")

    adapter = make_mock_llm_adapter()
    coder = _load_data_science_coder()(llm_adapter=adapter)
    experiment = ExperimentNode(
        node_id="node-1",
        run_id="run-1",
        branch_id="main",
        workspace_ref=str(workspace),
    )
    proposal = Proposal(proposal_id="proposal-1", summary="generate robust ds pipeline", constraints=[])
    scenario = ScenarioContext(
        run_id="run-1",
        scenario_name="data_science",
        input_payload={"data_source": str(data_source)},
        task_summary="contract test",
    )
    return coder, experiment, proposal, scenario, workspace


def _configure_adapter_for_codegen(
    monkeypatch,
    coder: Any,
    workspace: Path,
    code: str | None,
) -> None:
    adapter = coder._llm_adapter
    assert adapter is not None

    monkeypatch.setattr(
        adapter,
        "generate_structured",
        lambda *args, **kwargs: CodeDraft(
            artifact_id="artifact-structured",
            description="metadata-only",
            location=str(workspace),
        ),
    )
    monkeypatch.setattr(
        adapter,
        "generate_code",
        lambda *args, **kwargs: (
            CodeDraft(artifact_id="artifact-llm", description="llm draft", location=str(workspace)),
            code,
        ),
    )


def test_develop_writes_llm_code_not_template(tmp_path: Path, monkeypatch) -> None:
    coder, experiment, proposal, scenario, workspace = _build_inputs(tmp_path)
    llm_code = _llm_code()
    _configure_adapter_for_codegen(monkeypatch, coder, workspace, llm_code)

    coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)
    pipeline_text = (workspace / "pipeline.py").read_text(encoding="utf-8")

    assert pipeline_text == llm_code
    assert "import csv" not in pipeline_text
    assert "column_count" not in pipeline_text


def test_develop_code_is_executable(tmp_path: Path, monkeypatch) -> None:
    coder, experiment, proposal, scenario, workspace = _build_inputs(tmp_path)
    llm_code = _llm_code()
    _configure_adapter_for_codegen(monkeypatch, coder, workspace, llm_code)

    coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)
    pipeline_text = (workspace / "pipeline.py").read_text(encoding="utf-8")

    assert pipeline_text == llm_code
    compile(pipeline_text, str(workspace / "pipeline.py"), "exec")


def test_develop_code_contains_metrics_write(tmp_path: Path, monkeypatch) -> None:
    coder, experiment, proposal, scenario, workspace = _build_inputs(tmp_path)
    llm_code = _llm_code()
    _configure_adapter_for_codegen(monkeypatch, coder, workspace, llm_code)

    coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)
    pipeline_text = (workspace / "pipeline.py").read_text(encoding="utf-8")

    assert "with open('metrics.json', 'w') as f:" in pipeline_text
    assert "json.dump(metrics, f)" in pipeline_text


def test_develop_code_no_placeholders(tmp_path: Path, monkeypatch) -> None:
    coder, experiment, proposal, scenario, workspace = _build_inputs(tmp_path)
    llm_code = _llm_code() + "# GENERATED_BY_LLM\n"
    _configure_adapter_for_codegen(monkeypatch, coder, workspace, llm_code)

    coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)
    pipeline_text = (workspace / "pipeline.py").read_text(encoding="utf-8")

    assert "# GENERATED_BY_LLM" in pipeline_text
    assert "{{" not in pipeline_text
    assert "TODO" not in pipeline_text


def test_develop_fallback_on_mock_provider_returns_none(tmp_path: Path, monkeypatch) -> None:
    coder, experiment, proposal, scenario, workspace = _build_inputs(tmp_path)
    _configure_adapter_for_codegen(monkeypatch, coder, workspace, None)

    artifact = coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)
    pipeline_text = (workspace / "pipeline.py").read_text(encoding="utf-8")

    assert "row_count = 0" in pipeline_text
    assert experiment.hypothesis.get("_code_source") == "template_fallback"
    assert "code_source=template_fallback" in artifact.description


def test_develop_sets_code_source_trace(tmp_path: Path, monkeypatch) -> None:
    coder, experiment, proposal, scenario, workspace = _build_inputs(tmp_path)
    _configure_adapter_for_codegen(monkeypatch, coder, workspace, _llm_code())

    coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)

    assert experiment.hypothesis.get("_code_source") == "llm"


def test_develop_code_has_data_source(tmp_path: Path, monkeypatch) -> None:
    coder, experiment, proposal, scenario, workspace = _build_inputs(tmp_path)
    _configure_adapter_for_codegen(monkeypatch, coder, workspace, _llm_code())

    coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)
    pipeline_text = (workspace / "pipeline.py").read_text(encoding="utf-8")

    assert "data_source =" in pipeline_text
    assert "pd.read_csv(data_source)" in pipeline_text


def test_develop_artifact_description_has_code(tmp_path: Path, monkeypatch) -> None:
    coder, experiment, proposal, scenario, workspace = _build_inputs(tmp_path)
    _configure_adapter_for_codegen(monkeypatch, coder, workspace, _llm_code())

    artifact = coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)

    assert len(artifact.description) > 100
    assert "metrics.json" in artifact.description


def test_debug_sampling_works_with_llm_code(tmp_path: Path) -> None:
    plugin_path = Path(__file__).resolve().parents[1] / "scenarios" / "data_science" / "plugin.py"
    module_name = "data_science_runner_plugin_under_test"
    spec = importlib.util.spec_from_file_location(module_name, plugin_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    class _BackendStub:
        def execute(self, **kwargs):
            return types.SimpleNamespace(
                stdout="ok",
                stderr="",
                exit_code=0,
                timed_out=False,
                artifact_paths=[],
                artifact_manifest={"paths": []},
                outcome=None,
                duration_sec=0.01,
            )

    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    pipeline_path = workspace / "pipeline.py"
    pipeline_path.write_text(
        'data_source = "original_llm.csv"\n'
        "import json\n"
        "with open('metrics.json', 'w', encoding='utf-8') as f:\n"
        "    json.dump({'ok': True}, f)\n",
        encoding="utf-8",
    )

    real_data_source = tmp_path / "train.csv"
    real_data_source.write_text("id,x,y\n1,10,1\n2,11,0\n3,12,1\n", encoding="utf-8")

    runner = module.DataScienceRunner(backend=_BackendStub())
    scenario = ScenarioContext(
        run_id="run-debug-sampling",
        scenario_name="data_science",
        input_payload={"data_source": str(real_data_source), "command": "python3 pipeline.py"},
        config={"debug_config": DebugConfig(debug_mode=True, sample_fraction=0.5, supports_debug_sampling=True)},
    )
    artifact = CodeArtifact(
        artifact_id="artifact-debug-sampling",
        description="llm generated",
        location=str(workspace),
    )

    _ = runner.run(artifact=artifact, scenario=scenario)
    updated_pipeline_text = pipeline_path.read_text(encoding="utf-8")
    expected_sampled_path = real_data_source.with_name(f"{real_data_source.stem}.debug_sample{real_data_source.suffix}")

    assert f"data_source = {str(expected_sampled_path)!r}" in updated_pipeline_text
    assert 'data_source = "original_llm.csv"' not in updated_pipeline_text
