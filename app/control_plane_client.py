"""DTO-oriented client for the V1 control plane."""

from __future__ import annotations

from typing import Any, Protocol

from data_models import Event
from service_contracts import (
    ArtifactDescriptor,
    ArtifactListResponse,
    BranchListResponse,
    BranchSummary,
    ErrorCode,
    RunControlResponse,
    RunCreateRequest,
    RunEventPageResponse,
    RunSummaryResponse,
    ScenarioManifest,
    ServiceContractError,
)


class _ResponseLike(Protocol):
    status_code: int

    def json(self) -> Any: ...


class _TransportLike(Protocol):
    def get(self, path: str, params: dict[str, Any] | None = None) -> _ResponseLike: ...

    def post(self, path: str, json: dict[str, Any] | None = None) -> _ResponseLike: ...


class ControlPlaneClient:
    """Small shared client for tests, UI control actions, and future remote callers."""

    def __init__(self, transport: _TransportLike) -> None:
        self._transport = transport

    def create_run(self, request: RunCreateRequest | dict[str, Any]) -> RunSummaryResponse:
        payload = request.to_dict() if isinstance(request, RunCreateRequest) else dict(request)
        return _parse_run_summary(self._unwrap(self._transport.post("/runs", json=payload)))

    def get_run(self, run_id: str) -> RunSummaryResponse:
        return _parse_run_summary(self._unwrap(self._transport.get(f"/runs/{run_id}")))

    def pause_run(self, run_id: str) -> RunControlResponse:
        return _parse_run_control(self._unwrap(self._transport.post(f"/runs/{run_id}/pause", json={})))

    def resume_run(self, run_id: str) -> RunControlResponse:
        return _parse_run_control(self._unwrap(self._transport.post(f"/runs/{run_id}/resume", json={})))

    def stop_run(self, run_id: str) -> RunControlResponse:
        return _parse_run_control(self._unwrap(self._transport.post(f"/runs/{run_id}/stop", json={})))

    def list_events(
        self,
        run_id: str,
        *,
        cursor: str | None = None,
        limit: int = 50,
        branch_id: str | None = None,
    ) -> RunEventPageResponse:
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if branch_id is not None:
            params["branch_id"] = branch_id
        return _parse_event_page(self._unwrap(self._transport.get(f"/runs/{run_id}/events", params=params)))

    def list_artifacts(self, run_id: str, *, branch_id: str | None = None) -> ArtifactListResponse:
        params = {"branch_id": branch_id} if branch_id is not None else None
        return _parse_artifact_page(self._unwrap(self._transport.get(f"/runs/{run_id}/artifacts", params=params)))

    def list_branches(self, run_id: str) -> BranchListResponse:
        return _parse_branch_page(self._unwrap(self._transport.get(f"/runs/{run_id}/branches")))

    def list_scenarios(self) -> list[ScenarioManifest]:
        payload = self._unwrap(self._transport.get("/scenarios"))
        return [ScenarioManifest.from_dict(item) for item in payload.get("items", [])]

    def health(self) -> dict[str, Any]:
        return dict(self._unwrap(self._transport.get("/health")))

    def _unwrap(self, response: _ResponseLike) -> dict[str, Any]:
        payload = response.json()
        if response.status_code >= 400:
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            raise ServiceContractError(
                code=str(error.get("code", ErrorCode.INTERNAL_ERROR)),
                message=str(error.get("message", "control plane request failed")),
                field=error.get("field"),
            )
        if not isinstance(payload, dict):
            raise ServiceContractError(
                code=ErrorCode.INTERNAL_ERROR,
                message="control plane returned a non-object payload",
            )
        return payload


def _parse_run_summary(payload: dict[str, Any]) -> RunSummaryResponse:
    return RunSummaryResponse(
        run_id=str(payload["run_id"]),
        scenario=str(payload["scenario"]),
        status=str(payload["status"]),
        active_branch_ids=list(payload.get("active_branch_ids", [])),
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
        stop_conditions=dict(payload.get("stop_conditions", {})),
        config_snapshot=dict(payload.get("config_snapshot", {})),
    )


def _parse_run_control(payload: dict[str, Any]) -> RunControlResponse:
    return RunControlResponse(
        run_id=str(payload["run_id"]),
        action=str(payload["action"]),
        status=str(payload["status"]),
        message=str(payload.get("message", "")),
    )


def _parse_event_page(payload: dict[str, Any]) -> RunEventPageResponse:
    return RunEventPageResponse(
        run_id=str(payload["run_id"]),
        items=[Event.from_dict(item) for item in payload.get("items", [])],
        next_cursor=str(payload["next_cursor"]) if payload.get("next_cursor") is not None else None,
        limit=int(payload.get("limit", 50)),
    )


def _parse_artifact_page(payload: dict[str, Any]) -> ArtifactListResponse:
    return ArtifactListResponse(
        run_id=str(payload["run_id"]),
        items=[
            ArtifactDescriptor(
                path=str(item["path"]),
                branch_id=str(item["branch_id"]) if item.get("branch_id") is not None else None,
            )
            for item in payload.get("items", [])
        ],
    )


def _parse_branch_page(payload: dict[str, Any]) -> BranchListResponse:
    return BranchListResponse(
        run_id=str(payload["run_id"]),
        items=[
            BranchSummary(
                branch_id=str(item["branch_id"]),
                head_node_id=str(item["head_node_id"]),
            )
            for item in payload.get("items", [])
        ],
    )
