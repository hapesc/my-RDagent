"""Task-21/22 control plane with FastAPI-compatible routing and shared DTO services."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from app.query_services import (
    load_artifact_page,
    load_branch_page,
    load_event_page,
    load_run_summary,
)
from app.runtime import build_runtime
from service_contracts import (
    ErrorCode,
    ErrorResponse,
    RunControlResponse,
    RunCreateRequest,
    RunSummaryResponse,
    ServiceContractError,
    StructuredError,
    resolve_step_override_config,
)

from .fastapi_compat import FastAPI, HTTPException, Query, status
from .run_supervisor import RunSupervisor


def build_control_plane_app(supervisor: Optional[RunSupervisor] = None) -> FastAPI:
    app = FastAPI(title="AgentRD Control Plane")
    app.state.supervisor = supervisor or RunSupervisor()

    @app.post("/runs")
    def create_run(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            runtime = build_runtime()
            request = RunCreateRequest.from_dict(payload)
            manifest = _require_scenario_manifest(runtime, request.scenario)
            run_session = app.state.supervisor.create_run(
                request=request,
                config_snapshot=_build_config_snapshot(runtime, request, manifest),
            )
            return RunSummaryResponse.from_run_session(run_session).to_dict()
        except ServiceContractError as exc:
            raise _http_error(exc.code, str(exc), field=exc.field)

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> Dict[str, Any]:
        runtime = build_runtime()
        summary = load_run_summary(runtime.config.sqlite_path, run_id)
        if summary is None:
            raise _http_error(ErrorCode.NOT_FOUND, f"run not found: {run_id}")
        return summary.to_dict()

    @app.post("/runs/{run_id}/pause")
    def pause_run(run_id: str) -> Dict[str, Any]:
        try:
            run_session = app.state.supervisor.pause_run(run_id)
            return RunControlResponse(
                run_id=run_id,
                action="pause",
                status=run_session.status.value,
                message="pause requested",
            ).to_dict()
        except KeyError as exc:
            raise _http_error(ErrorCode.NOT_FOUND, exc.args[0] if exc.args else str(exc))
        except ServiceContractError as exc:
            raise _http_error(exc.code, str(exc), field=exc.field)

    @app.post("/runs/{run_id}/resume")
    def resume_run(run_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = payload
        try:
            run_session = app.state.supervisor.resume_run(run_id)
            return RunControlResponse(
                run_id=run_id,
                action="resume",
                status=run_session.status.value,
                message="resume scheduled",
            ).to_dict()
        except KeyError as exc:
            raise _http_error(ErrorCode.NOT_FOUND, exc.args[0] if exc.args else str(exc))
        except ServiceContractError as exc:
            raise _http_error(exc.code, str(exc), field=exc.field)

    @app.post("/runs/{run_id}/stop")
    def stop_run(run_id: str) -> Dict[str, Any]:
        try:
            run_session = app.state.supervisor.stop_run(run_id)
            return RunControlResponse(
                run_id=run_id,
                action="stop",
                status=run_session.status.value,
                message="stop requested",
            ).to_dict()
        except KeyError as exc:
            raise _http_error(ErrorCode.NOT_FOUND, exc.args[0] if exc.args else str(exc))
        except ServiceContractError as exc:
            raise _http_error(exc.code, str(exc), field=exc.field)

    @app.get("/runs/{run_id}/events")
    def list_events(
        run_id: str,
        cursor: Optional[str] = Query(default=None),
        limit: int = Query(default=50),
        branch_id: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        try:
            runtime = build_runtime()
            summary = load_run_summary(runtime.config.sqlite_path, run_id)
            if summary is None:
                raise _http_error(ErrorCode.NOT_FOUND, f"run not found: {run_id}")
            return load_event_page(
                runtime.config.sqlite_path,
                run_id,
                branch_id=branch_id,
                cursor=cursor,
                limit=limit,
            ).to_dict()
        except ServiceContractError as exc:
            raise _http_error(exc.code, str(exc), field=exc.field)

    @app.get("/runs/{run_id}/artifacts")
    def list_artifacts(
        run_id: str,
        branch_id: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        runtime = build_runtime()
        summary = load_run_summary(runtime.config.sqlite_path, run_id)
        if summary is None:
            raise _http_error(ErrorCode.NOT_FOUND, f"run not found: {run_id}")
        return load_artifact_page(
            runtime.config.sqlite_path,
            runtime.config.workspace_root,
            runtime.config.artifact_root,
            run_id,
            branch_id=branch_id,
        ).to_dict()

    @app.get("/runs/{run_id}/branches")
    def list_branches(run_id: str) -> Dict[str, Any]:
        runtime = build_runtime()
        summary = load_run_summary(runtime.config.sqlite_path, run_id)
        if summary is None:
            raise _http_error(ErrorCode.NOT_FOUND, f"run not found: {run_id}")
        return load_branch_page(runtime.config.sqlite_path, run_id).to_dict()

    @app.get("/scenarios")
    def list_scenarios() -> Dict[str, Any]:
        runtime = build_runtime()
        return {"items": [manifest.to_dict() for manifest in runtime.plugin_registry.list_manifests()]}

    @app.get("/health")
    def health() -> Dict[str, Any]:
        runtime = build_runtime()
        sqlite_ok = Path(runtime.config.sqlite_path).exists()
        artifact_root = Path(runtime.config.artifact_root)
        artifact_root.mkdir(parents=True, exist_ok=True)
        docker_available = shutil.which("docker") is not None
        execution_backend_ok = docker_available or runtime.config.allow_local_execution
        llm_adapter_ok = True
        checks = {
            "sqlite": "ok" if sqlite_ok else "missing",
            "artifact_root": "ok" if artifact_root.exists() else "missing",
            "execution_backend": "ok" if execution_backend_ok else "degraded",
            "llm_adapter": "ok" if llm_adapter_ok else "degraded",
        }
        return {
            "status": (
                "ok"
                if sqlite_ok and artifact_root.exists() and llm_adapter_ok and execution_backend_ok
                else "degraded"
            ),
            "checks": checks,
            "details": {
                "docker_available": docker_available,
                "allow_local_execution": runtime.config.allow_local_execution,
                "registered_scenarios": runtime.plugin_registry.list_scenarios(),
            },
        }

    return app


def _http_error(code: str, message: str, field: Optional[str] = None) -> HTTPException:
    status_code = status.HTTP_400_BAD_REQUEST
    if code == ErrorCode.NOT_FOUND:
        status_code = status.HTTP_404_NOT_FOUND
    elif code == ErrorCode.INVALID_STATE:
        status_code = status.HTTP_409_CONFLICT
    elif code == ErrorCode.INTERNAL_ERROR:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(error=StructuredError(code=code, message=message, field=field)).to_dict(),
    )


def _require_scenario_manifest(runtime, scenario: str):
    manifest = runtime.plugin_registry.get_manifest(scenario)
    if manifest is None:
        raise _http_error(ErrorCode.UNSUPPORTED_SCENARIO, f"unsupported scenario: {scenario}", field="scenario")
    return manifest


def _build_config_snapshot(runtime, request: RunCreateRequest, manifest) -> Dict[str, Any]:
    effective_step_config = resolve_step_override_config(manifest.default_step_overrides, request.step_overrides)
    return {
        "scenario": request.scenario,
        "stop_conditions": request.stop_conditions.to_dict() if hasattr(request.stop_conditions, "to_dict") else {
            "max_loops": request.stop_conditions.max_loops,
            "max_steps": request.stop_conditions.max_steps,
            "max_duration_sec": request.stop_conditions.max_duration_sec,
        },
        "step_overrides": effective_step_config.to_dict(),
        "requested_step_overrides": request.step_overrides.to_dict(),
        "scenario_manifest": manifest.to_dict(),
        "runtime": {
            "sandbox_timeout_sec": runtime.config.sandbox_timeout_sec,
            "allow_local_execution": runtime.config.allow_local_execution,
            "default_scenario": runtime.config.default_scenario,
        },
    }
