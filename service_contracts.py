"""Shared V1 service contracts for CLI, UI, and future API surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from data_models import Event, RunSession, RunStatus, StopConditions, model_to_dict


def _qualified_field(field_prefix: str | None, field_name: str) -> str:
    return f"{field_prefix}.{field_name}" if field_prefix else field_name


@dataclass
class ModelSelectorConfig:
    """Provider/model selection for an LLM-backed step."""

    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    max_retries: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
        field_prefix: str | None = None,
    ) -> ModelSelectorConfig:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="model selector override must be an object",
                field=field_prefix,
            )
        payload = data or {}
        try:
            temperature = float(payload["temperature"]) if payload.get("temperature") is not None else None
            max_tokens = int(payload["max_tokens"]) if payload.get("max_tokens") is not None else None
            max_retries = int(payload["max_retries"]) if payload.get("max_retries") is not None else None
        except (TypeError, ValueError) as exc:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="model selector override contains invalid numeric values",
                field=field_prefix,
            ) from exc
        if temperature is not None and temperature < 0:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="temperature must be >= 0",
                field=_qualified_field(field_prefix, "temperature"),
            )
        if max_tokens is not None and max_tokens <= 0:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="max_tokens must be > 0",
                field=_qualified_field(field_prefix, "max_tokens"),
            )
        if max_retries is not None and max_retries < 0:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="max_retries must be >= 0",
                field=_qualified_field(field_prefix, "max_retries"),
            )
        return cls(
            provider=payload.get("provider"),
            model=payload.get("model"),
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )


@dataclass
class RunningStepConfig:
    """Execution-step overrides."""

    timeout_sec: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
        field_prefix: str | None = "step_overrides.running",
    ) -> RunningStepConfig:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="running override must be an object",
                field=field_prefix,
            )
        payload = data or {}
        try:
            timeout_sec = int(payload["timeout_sec"]) if payload.get("timeout_sec") is not None else None
        except (TypeError, ValueError) as exc:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="running override contains invalid timeout_sec",
                field=_qualified_field(field_prefix, "timeout_sec"),
            ) from exc
        if timeout_sec is not None and timeout_sec <= 0:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="timeout_sec must be > 0",
                field=_qualified_field(field_prefix, "timeout_sec"),
            )
        return cls(timeout_sec=timeout_sec)


@dataclass
class StepOverrideConfig:
    """Run-level step overrides, frozen for V1."""

    proposal: ModelSelectorConfig = field(default_factory=ModelSelectorConfig)
    coding: ModelSelectorConfig = field(default_factory=ModelSelectorConfig)
    running: RunningStepConfig = field(default_factory=RunningStepConfig)
    feedback: ModelSelectorConfig = field(default_factory=ModelSelectorConfig)

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
        *,
        field_prefix: str = "step_overrides",
    ) -> StepOverrideConfig:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="step_overrides must be an object",
                field=field_prefix,
            )
        payload = data or {}
        unknown_keys = sorted(set(payload.keys()) - {"proposal", "coding", "running", "feedback"})
        if unknown_keys:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message=f"unsupported step override keys: {', '.join(unknown_keys)}",
                field=field_prefix,
            )
        return cls(
            proposal=ModelSelectorConfig.from_dict(
                payload.get("proposal"),
                field_prefix=f"{field_prefix}.proposal",
            ),
            coding=ModelSelectorConfig.from_dict(
                payload.get("coding"),
                field_prefix=f"{field_prefix}.coding",
            ),
            running=RunningStepConfig.from_dict(
                payload.get("running"),
                field_prefix=f"{field_prefix}.running",
            ),
            feedback=ModelSelectorConfig.from_dict(
                payload.get("feedback"),
                field_prefix=f"{field_prefix}.feedback",
            ),
        )


def merge_model_selector_config(
    defaults: ModelSelectorConfig,
    override: ModelSelectorConfig | None = None,
) -> ModelSelectorConfig:
    current = override or ModelSelectorConfig()
    return ModelSelectorConfig(
        provider=current.provider if current.provider is not None else defaults.provider,
        model=current.model if current.model is not None else defaults.model,
        temperature=current.temperature if current.temperature is not None else defaults.temperature,
        max_tokens=current.max_tokens if current.max_tokens is not None else defaults.max_tokens,
        max_retries=current.max_retries if current.max_retries is not None else defaults.max_retries,
    )


def merge_running_step_config(
    defaults: RunningStepConfig,
    override: RunningStepConfig | None = None,
) -> RunningStepConfig:
    current = override or RunningStepConfig()
    return RunningStepConfig(
        timeout_sec=current.timeout_sec if current.timeout_sec is not None else defaults.timeout_sec,
    )


def resolve_step_override_config(
    defaults: StepOverrideConfig,
    override: StepOverrideConfig | None = None,
) -> StepOverrideConfig:
    current = override or StepOverrideConfig()
    return StepOverrideConfig(
        proposal=merge_model_selector_config(defaults.proposal, current.proposal),
        coding=merge_model_selector_config(defaults.coding, current.coding),
        running=merge_running_step_config(defaults.running, current.running),
        feedback=merge_model_selector_config(defaults.feedback, current.feedback),
    )


@dataclass
class ScenarioManifest:
    """Shared scenario capability description for CLI, UI, and API."""

    scenario_name: str
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    supports_branching: bool = True
    supports_resume: bool = True
    supports_local_execution: bool = False
    supported_step_overrides: list[str] = field(default_factory=lambda: ["proposal", "coding", "running", "feedback"])
    default_step_overrides: StepOverrideConfig = field(default_factory=StepOverrideConfig)

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioManifest:
        if not isinstance(data, dict):
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="scenario manifest must be an object",
            )
        return cls(
            scenario_name=str(data.get("scenario_name", "")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            tags=list(data.get("tags", [])),
            supports_branching=bool(data.get("supports_branching", True)),
            supports_resume=bool(data.get("supports_resume", True)),
            supports_local_execution=bool(data.get("supports_local_execution", False)),
            supported_step_overrides=list(
                data.get("supported_step_overrides", ["proposal", "coding", "running", "feedback"])
            ),
            default_step_overrides=StepOverrideConfig.from_dict(
                data.get("default_step_overrides"),
                field_prefix="default_step_overrides",
            ),
        )


class ErrorCode(str):
    """Stable V1 error codes."""

    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    INVALID_STATE = "invalid_state"
    UNSUPPORTED_SCENARIO = "unsupported_scenario"
    INTERNAL_ERROR = "internal_error"


class ServiceContractError(ValueError):
    """Structured validation error used across CLI/UI/API entrypoints."""

    def __init__(self, code: str, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


@dataclass
class StructuredError:
    """Structured error payload shared by CLI and future API."""

    code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)


@dataclass
class ErrorResponse:
    """Top-level structured error response."""

    error: StructuredError

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_error(cls, error: ServiceContractError) -> ErrorResponse:
        return cls(error=StructuredError(code=error.code, message=str(error), field=error.field))


@dataclass
class RunCreateRequest:
    """Create-run DTO for V1."""

    scenario: str
    task_summary: str
    run_id: str | None = None
    entry_input: dict[str, Any] = field(default_factory=dict)
    stop_conditions: StopConditions = field(default_factory=StopConditions)
    step_overrides: StepOverrideConfig = field(default_factory=StepOverrideConfig)

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunCreateRequest:
        if not isinstance(data, dict):
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="run create request must be an object",
            )
        scenario = str(data.get("scenario", "")).strip()
        if not scenario:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="scenario must not be empty",
                field="scenario",
            )
        task_summary = str(data.get("task_summary", "")).strip()
        if not task_summary:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="task_summary must not be empty",
                field="task_summary",
            )
        entry_input = data.get("entry_input", {})
        if entry_input is None:
            entry_input = {}
        if not isinstance(entry_input, dict):
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="entry_input must be an object",
                field="entry_input",
            )
        stop_conditions = data.get("stop_conditions", {})
        if stop_conditions is None:
            stop_conditions = {}
        if not isinstance(stop_conditions, dict):
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="stop_conditions must be an object",
                field="stop_conditions",
            )
        try:
            return cls(
                scenario=scenario,
                task_summary=task_summary,
                run_id=str(data["run_id"]) if data.get("run_id") is not None else None,
                entry_input=dict(entry_input),
                stop_conditions=StopConditions(
                    max_loops=int(stop_conditions.get("max_loops", data.get("max_loops", 1))),
                    max_steps=(
                        int(stop_conditions["max_steps"]) if stop_conditions.get("max_steps") is not None else None
                    ),
                    max_duration_sec=int(stop_conditions.get("max_duration_sec", data.get("max_duration_sec", 300))),
                ),
                step_overrides=StepOverrideConfig.from_dict(data.get("step_overrides")),
            )
        except ServiceContractError:
            raise
        except (TypeError, ValueError) as exc:
            raise ServiceContractError(
                code=ErrorCode.INVALID_REQUEST,
                message="run create request contains invalid numeric values",
                field="stop_conditions",
            ) from exc


@dataclass
class RunSummaryResponse:
    """Run summary DTO."""

    run_id: str
    scenario: str
    status: str
    active_branch_ids: list[str]
    created_at: str
    updated_at: str
    stop_conditions: dict[str, Any]
    config_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_run_session(cls, run_session: RunSession) -> RunSummaryResponse:
        payload = run_session.to_dict()
        return cls(
            run_id=run_session.run_id,
            scenario=run_session.scenario,
            status=run_session.status.value if isinstance(run_session.status, RunStatus) else str(run_session.status),
            active_branch_ids=list(run_session.active_branch_ids),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            stop_conditions=dict(payload["stop_conditions"]),
            config_snapshot=dict(run_session.config_snapshot),
        )


@dataclass
class RunControlResponse:
    """Pause/resume/stop response DTO."""

    run_id: str
    action: str
    status: str
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)


@dataclass
class RunEventPageResponse:
    """Cursor-based event page contract."""

    run_id: str
    items: list[Event] = field(default_factory=list)
    next_cursor: str | None = None
    limit: int = 50

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)


@dataclass
class ArtifactDescriptor:
    """Artifact listing contract."""

    path: str
    branch_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)


@dataclass
class ArtifactListResponse:
    """Artifact page contract."""

    run_id: str
    items: list[ArtifactDescriptor] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)


@dataclass
class BranchSummary:
    """Branch listing contract."""

    branch_id: str
    head_node_id: str

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)


@dataclass
class BranchListResponse:
    """Branch list contract."""

    run_id: str
    items: list[BranchSummary] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return model_to_dict(self)
