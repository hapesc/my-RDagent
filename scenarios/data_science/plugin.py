"""Data Science scenario plugin v1."""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.execution import DockerExecutionBackend, DockerExecutionBackendConfig
from data_models import (
    CodeArtifact,
    ContextPack,
    ExecutionResult,
    ExperimentNode,
    FeedbackRecord,
    LoopState,
    Plan,
    Proposal,
    RunSession,
    Score,
    StepState,
)
from evaluation_service.stratified_splitter import StratifiedSplitter
from llm import (
    CodeDraft,
    FeedbackDraft,
    LLMAdapter,
    MockLLMProvider,
    ProposalDraft,
    coding_prompt,
    feedback_prompt,
    proposal_prompt,
)
from llm.codegen import CODE_SOURCE_FAILED, CODE_SOURCE_LLM, CODE_SOURCE_TEMPLATE, emit_code_source_event
from llm.codegen.quality_gate import CodegenQualityGate, QualityResult
from llm.codegen.validators import (
    compile_check,
    detect_placeholders,
    has_placeholder,
    validate_compile,
    validate_content,
)
from plugins.contracts import (
    Coder,
    ExperimentGenerator,
    FeedbackAnalyzer,
    PluginBundle,
    ProposalEngine,
    Runner,
    ScenarioContext,
    ScenarioPlugin,
    UsefulnessGateInput,
)
from service_contracts import ModelSelectorConfig, RunningStepConfig, StepOverrideConfig

if TYPE_CHECKING:
    from core.reasoning.pipeline import ReasoningPipeline
    from core.reasoning.virtual_eval import VirtualEvaluator


_EXPERIMENT_METRICS = {"accuracy", "f1", "precision", "recall", "rmse", "mae", "r2", "auc", "log_loss"}


def evaluate_data_science_quality(code: str, metrics: dict[str, object]) -> QualityResult:
    reasons: list[str] = []
    if has_placeholder(code):
        reasons.append("placeholder code detected")
    if not compile_check(code):
        reasons.append("code does not compile")

    metric_keys = {str(key).lower() for key in metrics}
    has_experiment_metric = any(
        metric == key or key.startswith(f"{metric}_") or key.endswith(f"_{metric}")
        for metric in _EXPERIMENT_METRICS
        for key in metric_keys
    )
    if not has_experiment_metric:
        reasons.append("missing experiment metric (need one of: accuracy, f1, rmse, etc.)")

    return QualityResult(passed=not reasons, reasons=reasons, extracted_code=code, metadata=metrics)


def _clamp_sample_fraction(value: float) -> float:
    """Clamp sample_fraction to valid range [0.0, 1.0]."""
    return max(0.0, min(value, 1.0))


def default_data_science_step_overrides(timeout_sec: int = 300) -> StepOverrideConfig:
    return StepOverrideConfig(
        proposal=ModelSelectorConfig(provider="mock", model="ds-proposal-default", max_retries=2),
        coding=ModelSelectorConfig(
            provider="mock",
            model="ds-coding-default",
            max_retries=2,
            max_tokens=2048,
        ),
        running=RunningStepConfig(timeout_sec=timeout_sec),
        feedback=ModelSelectorConfig(provider="mock", model="ds-feedback-default", max_retries=2),
    )


@dataclass
class DataScienceV1Config:
    """Configuration for Data Science plugin v1."""

    workspace_root: str = "/tmp/rd_agent_workspace"
    trace_storage_path: str = "/tmp/rd_agent_trace/events.jsonl"
    docker_image: str = "python:3.11-slim"
    prefer_docker: bool = True
    allow_local_execution: bool = False
    default_step_overrides: StepOverrideConfig = field(default_factory=default_data_science_step_overrides)


class DataScienceScenarioPlugin(ScenarioPlugin):
    def build_context(self, run_session: RunSession, input_payload: dict[str, Any]) -> ScenarioContext:
        split_manifest = _build_data_science_split_manifest(input_payload)
        return ScenarioContext(
            run_id=run_session.run_id,
            scenario_name=run_session.scenario,
            input_payload=dict(input_payload),
            config={"split_manifest": split_manifest},
            task_summary=str(input_payload.get("task_summary", "")),
            step_config=StepOverrideConfig.from_dict(input_payload.get("step_config")),
        )


def _build_data_science_split_manifest(input_payload: dict[str, Any]) -> dict[str, Any] | None:
    data_ids = _normalize_id_list(input_payload.get("data_ids"))
    labels = _normalize_label_list(input_payload.get("labels"))

    if not data_ids:
        rows = _load_data_rows(str(input_payload.get("data_source", "")).strip())
        if rows:
            data_ids, labels = _extract_split_inputs_from_rows(rows, input_payload)

    if not data_ids:
        return None

    splitter = StratifiedSplitter(
        train_ratio=_resolve_split_ratio(input_payload.get("train_ratio"), 0.9),
        test_ratio=_resolve_split_ratio(input_payload.get("test_ratio"), 0.1),
        seed=_resolve_split_seed(input_payload.get("split_seed", input_payload.get("seed", 42))),
    )
    manifest = splitter.split(data_ids, labels=labels)
    return asdict(manifest)


def _load_data_rows(data_source: str) -> list[dict[str, Any]]:
    if not data_source:
        return []

    path = Path(data_source)
    if not path.exists() or not path.is_file():
        return []

    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if suffix in {".jsonl", ".ndjson"}:
        rows: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if isinstance(record, dict):
                    rows.append(record)
        return rows
    return []


def _extract_split_inputs_from_rows(
    rows: list[dict[str, Any]], input_payload: dict[str, Any]
) -> tuple[list[str], list[str] | None]:
    id_column = str(input_payload.get("id_column", "")).strip() or _first_matching_key(
        rows,
        ["id", "data_id", "row_id", "item_id"],
    )
    label_column = str(input_payload.get("label_column", "")).strip() or _first_matching_key(
        rows,
        ["label", "target", "y", "class", "category"],
    )

    data_ids = [str(row.get(id_column) or index) for index, row in enumerate(rows)]
    labels: list[str] | None = None
    if label_column:
        candidate_labels = [str(row.get(label_column, "")) for row in rows]
        if any(label.strip() for label in candidate_labels):
            labels = candidate_labels
    return data_ids, labels


def _first_matching_key(rows: list[dict[str, Any]], candidates: list[str]) -> str:
    if not rows:
        return ""
    first_row = rows[0]
    for candidate in candidates:
        if candidate in first_row:
            return candidate
    return ""


def _normalize_id_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalize_label_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    labels = [str(item) for item in value]
    return labels if labels else None


def _resolve_split_ratio(value: Any, default: float) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return default
    return resolved if resolved > 0 else default


def _resolve_split_seed(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 42


def _load_validate_code_safety_func() -> Any:
    from scenarios.data_science.code_safety import validate_code_safety

    return validate_code_safety


def _is_mock_llm_adapter(adapter: LLMAdapter) -> bool:
    provider = getattr(adapter, "_provider", None)
    return provider is not None and isinstance(provider, MockLLMProvider)


def _should_allow_metrics_open_write(safety_violations: list[str], code: str) -> list[str]:
    if "metrics.json" not in code:
        return safety_violations
    return [v for v in safety_violations if v != "Dangerous file write call: 'open()'"]


def _ensure_data_source_binding(code: str, data_source: str) -> str:
    """Prepend ``data_source = ...`` when the generated code lacks one.

    LLM-generated code may omit a ``data_source`` assignment because the
    prompt only asks the model to *use* the variable, not define it.  In
    that case we inject the binding so the script is self-contained.
    """
    if "data_source =" in code:
        return code
    return f"data_source = {data_source!r}\n" + code


class DataScienceProposalEngine(ProposalEngine):
    def __init__(
        self,
        llm_adapter: LLMAdapter,
        reasoning_pipeline: ReasoningPipeline | None = None,
        virtual_evaluator: VirtualEvaluator | None = None,
    ) -> None:
        self._llm_adapter = llm_adapter
        self._reasoning_pipeline = reasoning_pipeline
        self._virtual_evaluator = virtual_evaluator

    def propose(
        self,
        task_summary: str,
        context: ContextPack,
        parent_ids: list[str],
        plan: Plan,
        scenario: ScenarioContext,
    ) -> Proposal:
        summary = task_summary or scenario.task_summary or "data science task"
        highlights = list(getattr(context, "highlights", None) or [])
        scored_items = list(getattr(context, "scored_items", None) or [])
        context_lines: list[str] = [f"- {item}" for item in highlights if str(item).strip()]
        for item, score in scored_items[:3]:
            item_text = str(item).strip()
            if not item_text:
                continue
            try:
                score_text = f"{float(score):.3f}"
            except (TypeError, ValueError):
                score_text = "N/A"
            context_lines.append(f"- {item_text} (score={score_text})")
        if not context_lines:
            context_lines = ["- None"]

        guidance_items = list(getattr(plan, "guidance", None) or []) if plan is not None else []
        guidance_text = (
            "\n".join(f"- {str(item).strip()}" for item in guidance_items if str(item).strip())
            or "No specific guidance"
        )
        parent_text = ", ".join(parent_ids) if parent_ids else "None"
        context_text = "\n".join(context_lines)
        enriched_summary = (
            f"{summary}\n\n"
            f"Prior Context:\n{context_text}\n\n"
            f"Strategic Guidance:\n{guidance_text}\n\n"
            f"Parent Branch Continuity:\n{parent_text}"
        )
        iteration = int(scenario.input_payload.get("loop_index", 0))

        if self._virtual_evaluator is not None:
            from core.reasoning.virtual_eval import VirtualEvaluator

            evaluator = self._virtual_evaluator
            if isinstance(evaluator, VirtualEvaluator):
                previous_results = [str(result) for result in scenario.input_payload.get("previous_results", [])]
                current_scores = [float(score) for score in scenario.input_payload.get("current_scores", [])]
                designs = evaluator.evaluate(
                    task_summary=enriched_summary,
                    scenario_name=scenario.scenario_name,
                    iteration=iteration,
                    previous_results=previous_results,
                    current_scores=current_scores,
                    model_config=scenario.step_config.proposal,
                )
                if designs:
                    best = designs[0]
                    constraints = list(best.constraints)
                    if scenario.step_config.proposal.model:
                        constraints.append(f"model:{scenario.step_config.proposal.model}")
                    return Proposal(
                        proposal_id="proposal-ds-fc3",
                        summary=best.summary,
                        constraints=constraints,
                        virtual_score=best.virtual_score,
                    )

        if self._reasoning_pipeline is not None:
            from core.reasoning.pipeline import ReasoningPipeline

            pipeline = self._reasoning_pipeline
            if isinstance(pipeline, ReasoningPipeline):
                previous_results = [str(result) for result in scenario.input_payload.get("previous_results", [])]
                current_scores = [float(score) for score in scenario.input_payload.get("current_scores", [])]
                design = pipeline.reason(
                    task_summary=enriched_summary,
                    scenario_name=scenario.scenario_name,
                    iteration=iteration,
                    previous_results=previous_results,
                    current_scores=current_scores,
                    model_config=scenario.step_config.proposal,
                )
                constraints = list(design.constraints)
                if scenario.step_config.proposal.model:
                    constraints.append(f"model:{scenario.step_config.proposal.model}")
                return Proposal(
                    proposal_id="proposal-ds-fc3-pipeline",
                    summary=design.summary,
                    constraints=constraints,
                    virtual_score=design.virtual_score,
                )

        prompt = proposal_prompt(
            task_summary=enriched_summary,
            scenario_name=scenario.scenario_name,
            iteration=iteration,
        )
        draft = self._llm_adapter.generate_structured(
            prompt,
            ProposalDraft,
            model_config=scenario.step_config.proposal,
        )
        return Proposal(
            proposal_id="proposal-ds-v1",
            summary=draft.summary,
            constraints=draft.constraints,
            virtual_score=draft.virtual_score,
        )


class DataScienceExperimentGenerator(ExperimentGenerator):
    def __init__(self, workspace_root: str) -> None:
        self._workspace_root = Path(workspace_root)

    def generate(
        self,
        proposal: Proposal,
        run_session: RunSession,
        loop_state: LoopState,
        parent_ids: list[str],
    ) -> ExperimentNode:
        branch_id = run_session.active_branch_ids[0] if run_session.active_branch_ids else "main"
        parent_node_id: str | None = parent_ids[0] if parent_ids else None
        node_id = f"node-{run_session.run_id}-{branch_id}-{loop_state.iteration}"
        workspace_ref = self._workspace_root / run_session.run_id / node_id
        return ExperimentNode(
            node_id=node_id,
            run_id=run_session.run_id,
            branch_id=branch_id,
            parent_node_id=parent_node_id,
            loop_index=loop_state.iteration,
            step_state=StepState.EXPERIMENT_READY,
            hypothesis={"text": proposal.summary, "component": "DataScience"},
            workspace_ref=str(workspace_ref),
            result_ref=str(workspace_ref / "result"),
            feedback_ref="",
        )


def _emit_ds_code_source(
    code_source: str,
    experiment: ExperimentNode,
    errors: list[str] | None = None,
) -> None:
    details: dict[str, Any] = {
        "run_id": experiment.run_id,
        "branch_id": experiment.branch_id,
        "loop_index": experiment.loop_index,
        "node_id": experiment.node_id,
    }
    if code_source != CODE_SOURCE_TEMPLATE:
        details["round"] = experiment.loop_index
    if errors:
        details["errors"] = errors
    if isinstance(experiment.hypothesis, dict):
        experiment.hypothesis["_code_source"] = code_source
    emit_code_source_event(code_source, "data_science", details)


class DataScienceCoder(Coder):
    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        self._llm_adapter = llm_adapter

    def develop(
        self,
        experiment: ExperimentNode,
        proposal: Proposal,
        scenario: ScenarioContext,
    ) -> CodeArtifact:
        workspace = Path(experiment.workspace_ref)
        workspace.mkdir(parents=True, exist_ok=True)

        data_source = str(scenario.input_payload.get("data_source", ""))
        readme_text = proposal.summary
        artifact_id = f"artifact-{experiment.node_id}"

        proposal_summary_with_feedback = self._enrich_proposal_with_feedback(proposal, experiment)
        validate_code_safety = _load_validate_code_safety_func()

        if self._llm_adapter is not None:
            prompt = coding_prompt(
                proposal_summary=proposal_summary_with_feedback,
                constraints=proposal.constraints,
                experiment_node_id=experiment.node_id,
                workspace_ref=experiment.workspace_ref,
                scenario_name=scenario.scenario_name,
                scenario_type="data_science",
            )
            try:
                code_draft, generated_code = self._llm_adapter.generate_code(
                    prompt,
                    CodeDraft,
                    model_config=scenario.step_config.coding,
                )
            except Exception as exc:
                _emit_ds_code_source(CODE_SOURCE_FAILED, experiment, [f"generate_code failed: {exc}"])
                raise RuntimeError("data_science code generation failed") from exc

            if not generated_code:
                if _is_mock_llm_adapter(self._llm_adapter):
                    pipeline_script = self._build_pipeline_script(data_source=data_source)
                    (workspace / "pipeline.py").write_text(pipeline_script, encoding="utf-8")
                    _emit_ds_code_source(CODE_SOURCE_TEMPLATE, experiment)
                    readme_text = f"{code_draft.description}\n{pipeline_script}\n\ncode_source=template"
                    (workspace / "README.txt").write_text(readme_text, encoding="utf-8")
                    return CodeArtifact(
                        artifact_id=artifact_id,
                        description=readme_text,
                        location=str(workspace),
                    )
                _emit_ds_code_source(CODE_SOURCE_FAILED, experiment, ["generate_code returned empty code"])
                raise RuntimeError("data_science code generation returned empty code")

            generated_code = _ensure_data_source_binding(generated_code, data_source)

            # --- PR #12 CoSTEER validation pipeline ---
            compile_result = validate_compile(generated_code)
            safety_result = validate_code_safety(generated_code)
            placeholder_result = detect_placeholders(generated_code)
            content_result = validate_content(generated_code, required_patterns=["data_source", "metrics.json"])
            safety_violations = _should_allow_metrics_open_write(safety_result.violations, generated_code)

            errors: list[str] = []
            if not compile_result.valid:
                errors.extend(compile_result.errors)
            if safety_violations:
                errors.extend(safety_violations)
            if not placeholder_result.valid:
                errors.extend(placeholder_result.errors)
            if not content_result.valid:
                errors.extend(content_result.errors)

            if errors:
                _emit_ds_code_source(CODE_SOURCE_FAILED, experiment, errors)
                raise RuntimeError(f"data_science code validation failed: {'; '.join(errors)}")

            artifact_id = code_draft.artifact_id

            pipeline_script = generated_code
            (workspace / "pipeline.py").write_text(pipeline_script, encoding="utf-8")
            _emit_ds_code_source(CODE_SOURCE_LLM, experiment)
            readme_text = pipeline_script
        else:
            pipeline_script = self._build_pipeline_script(data_source=data_source)
            (workspace / "pipeline.py").write_text(pipeline_script, encoding="utf-8")
            _emit_ds_code_source(CODE_SOURCE_TEMPLATE, experiment)
            readme_text = f"{pipeline_script}\n\ncode_source=template"
        (workspace / "README.txt").write_text(readme_text, encoding="utf-8")

        return CodeArtifact(
            artifact_id=artifact_id,
            description=readme_text,
            location=str(workspace),
        )

    def _enrich_proposal_with_feedback(self, proposal: Proposal, experiment: ExperimentNode) -> str:
        feedback_text = None
        if isinstance(experiment.hypothesis, dict):
            feedback_text = experiment.hypothesis.get("_costeer_feedback")

        if feedback_text and isinstance(feedback_text, str) and feedback_text.strip():
            return f"{proposal.summary}\n\nPrevious round feedback:\n{feedback_text}"
        return proposal.summary

    def _build_pipeline_script(self, data_source: str) -> str:
        return (
            "import csv\n"
            "import json\n"
            "import os\n"
            f"data_source = {data_source!r}\n"
            "row_count = 0\n"
            "column_count = 0\n"
            "if data_source and os.path.exists(data_source):\n"
            "    with open(data_source, newline='', encoding='utf-8') as handle:\n"
            "        reader = csv.DictReader(handle)\n"
            "        column_count = len(reader.fieldnames or [])\n"
            "        row_count = sum(1 for _ in reader)\n"
            "metrics = {'row_count': row_count, 'column_count': column_count, 'status': 'ok'}\n"
            "with open('metrics.json', 'w', encoding='utf-8') as handle:\n"
            "    json.dump(metrics, handle)\n"
            "print(json.dumps(metrics))\n"
        )


class DataScienceRunner(Runner):
    def __init__(self, backend: DockerExecutionBackend) -> None:
        self._backend = backend

    def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult:
        logger = logging.getLogger(__name__)
        loop_index = int(scenario.input_payload.get("loop_index", 0))
        branch_id = str(scenario.input_payload.get("branch_id", "main"))
        command = str(scenario.input_payload.get("command", "python3 pipeline.py"))
        debug_config = scenario.config.get("debug_config")
        if (
            debug_config
            and getattr(debug_config, "debug_mode", False)
            and getattr(debug_config, "supports_debug_sampling", False)
        ):
            sample_fraction = float(getattr(debug_config, "sample_fraction", 0.1))
            sample_fraction = _clamp_sample_fraction(sample_fraction)

            if sample_fraction == 0.0:
                logger.warning("Debug mode: sample_fraction=0 detected; using full dataset (minimum 1 row)")

            data_source = str(scenario.input_payload.get("data_source", "")).strip()
            if data_source:
                data_path = Path(data_source)
                pipeline_path = Path(artifact.location) / "pipeline.py"
                if data_path.exists() and data_path.is_file() and pipeline_path.exists():
                    sampled_path = data_path.with_name(f"{data_path.stem}.debug_sample{data_path.suffix}")
                    source_lines = data_path.read_text(encoding="utf-8").splitlines()
                    if len(source_lines) > 1:
                        header, rows = source_lines[0], source_lines[1:]
                        sample_size = max(1, int(len(rows) * sample_fraction))
                        sampled_content = "\n".join([header, *rows[:sample_size]]) + "\n"
                        sampled_path.write_text(sampled_content, encoding="utf-8")
                        pipeline_text = pipeline_path.read_text(encoding="utf-8")
                        pipeline_text = re.sub(
                            r"data_source\s*=\s*[^\n]+",
                            f"data_source = {str(sampled_path)!r}",
                            pipeline_text,
                            count=1,
                        )
                        pipeline_path.write_text(pipeline_text, encoding="utf-8")
                        logger.info(
                            "Debug mode active: sampling %.0f%% of data",
                            sample_fraction * 100,
                        )
        backend_result = self._backend.execute(
            run_id=scenario.run_id,
            branch_id=branch_id,
            loop_index=loop_index,
            workspace_path=artifact.location,
            command=command,
            timeout_sec=scenario.step_config.running.timeout_sec,
        )
        logs = backend_result.stdout if backend_result.stdout else backend_result.stderr
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=backend_result.exit_code,
            logs_ref=logs,
            artifacts_ref=json.dumps(backend_result.artifact_paths),
            duration_sec=backend_result.duration_sec,
            timed_out=backend_result.timed_out,
            artifact_manifest=backend_result.artifact_manifest,
            outcome=backend_result.outcome,
        )


class DataScienceFeedbackAnalyzer(FeedbackAnalyzer):
    def __init__(self, llm_adapter: LLMAdapter) -> None:
        self._llm_adapter = llm_adapter

    def summarize(
        self,
        experiment: ExperimentNode,
        result: ExecutionResult,
        score: Score | None = None,
    ) -> FeedbackRecord:
        score_text = "none" if score is None else f"{score.metric_name}:{score.value:.4f}"
        hypothesis_text = (
            experiment.hypothesis.get("text", "")
            if isinstance(experiment.hypothesis, dict)
            else str(experiment.hypothesis)
        )
        iteration = experiment.loop_index
        feedback_config = ModelSelectorConfig.from_dict(
            experiment.hypothesis.get("_feedback_model_config") if isinstance(experiment.hypothesis, dict) else None
        )
        prompt = feedback_prompt(
            hypothesis_text=hypothesis_text,
            exit_code=result.exit_code,
            score_text=score_text,
            logs_summary=result.logs_ref,
            iteration=iteration,
        )
        draft = self._llm_adapter.generate_structured(
            prompt,
            FeedbackDraft,
            model_config=feedback_config,
        )
        usefulness_eligible = result.resolve_outcome().usefulness_eligible
        return FeedbackRecord(
            feedback_id=f"fb-{experiment.node_id}",
            decision=draft.decision and usefulness_eligible,
            acceptable=draft.acceptable and usefulness_eligible,
            reason=draft.reason,
            observations=draft.observations,
            code_change_summary=draft.code_change_summary,
        )


def _validate_data_science_usefulness(gate_input: UsefulnessGateInput) -> str | None:
    payload = gate_input.structured_payload
    if not isinstance(payload, dict):
        return "missing structured payload"
    if "status" not in payload:
        return "missing key field: status"
    if "row_count" not in payload:
        return "missing key field: row_count"
    status_value = str(payload.get("status", "")).strip().lower()
    if status_value in {"", "todo", "tbd", "placeholder"}:
        return "template-only status"
    row_count = payload.get("row_count")
    if not isinstance(row_count, int):
        return "row_count must be integer"
    if row_count < 0:
        return "row_count cannot be negative"
    if _is_row_count_only_payload(payload):
        return "row-count-only payload"
    if not _has_informative_metrics(payload):
        return "missing informative metrics"
    return None


_DS_NON_INFORMATIVE_KEYS = {
    "status",
    "row_count",
    "result",
    "outcome",
    "message",
    "ok",
    "success",
    "state",
    "detail",
}

_DS_PLACEHOLDER_VALUES = {
    "",
    "todo",
    "tbd",
    "placeholder",
    "template",
    "n/a",
    "na",
    "unknown",
    "null",
}


def _is_row_count_only_payload(payload: dict[str, Any]) -> bool:
    keys = {str(key).strip().lower() for key in payload}
    return bool(keys) and keys.issubset({"status", "row_count"})


def _has_informative_metrics(payload: dict[str, Any]) -> bool:
    for key, value in payload.items():
        normalized_key = str(key).strip().lower()
        if normalized_key in _DS_NON_INFORMATIVE_KEYS:
            continue
        if _is_informative_value(value):
            return True
    return False


def _is_informative_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        normalized = value.strip().lower()
        return bool(normalized) and normalized not in _DS_PLACEHOLDER_VALUES
    if isinstance(value, dict):
        return any(_is_informative_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_is_informative_value(item) for item in value)
    return False


def build_data_science_v1_bundle(
    config: DataScienceV1Config | None = None,
    llm_adapter: LLMAdapter | None = None,
    reasoning_pipeline: ReasoningPipeline | None = None,
    virtual_evaluator: VirtualEvaluator | None = None,
) -> PluginBundle:
    """Build Data Science plugin v1 bundle."""

    plugin_config = config or DataScienceV1Config()
    if llm_adapter is None:
        raise RuntimeError(
            "llm_adapter is required for build_data_science_v1_bundle(). "
            "Configure a real LLM provider, e.g.: "
            "LLMAdapter(provider=LiteLLMProvider("
            "api_key=os.environ['OPENAI_API_KEY'], model='gpt-4o-mini'"
            "), config=LLMAdapterConfig(max_retries=2))"
        )
    adapter = llm_adapter
    backend = DockerExecutionBackend(
        DockerExecutionBackendConfig(
            docker_image=plugin_config.docker_image,
            prefer_docker=plugin_config.prefer_docker,
            allow_local_execution=plugin_config.allow_local_execution,
            default_timeout_sec=plugin_config.default_step_overrides.running.timeout_sec or 300,
            trace_storage_path=plugin_config.trace_storage_path,
        )
    )

    return PluginBundle(
        scenario_name="data_science",
        scenario_plugin=DataScienceScenarioPlugin(),
        proposal_engine=DataScienceProposalEngine(
            adapter,
            reasoning_pipeline=reasoning_pipeline,
            virtual_evaluator=virtual_evaluator,
        ),
        experiment_generator=DataScienceExperimentGenerator(workspace_root=plugin_config.workspace_root),
        coder=DataScienceCoder(adapter),
        runner=DataScienceRunner(backend),
        feedback_analyzer=DataScienceFeedbackAnalyzer(adapter),
        scene_usefulness_validator=_validate_data_science_usefulness,
        default_step_overrides=plugin_config.default_step_overrides,
    )
