"""Shared query services for control plane and UI."""

from __future__ import annotations

import json
from pathlib import Path

from core.storage import BranchTraceStore, BranchTraceStoreConfig, SQLiteMetadataStore, SQLiteStoreConfig
from service_contracts import (
    ArtifactDescriptor,
    ArtifactListResponse,
    BranchListResponse,
    BranchSummary,
    ErrorCode,
    RunEventPageResponse,
    RunSummaryResponse,
    ServiceContractError,
)


def load_run_summary(sqlite_path: str, run_id: str) -> RunSummaryResponse | None:
    store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path))
    run_session = store.get_run(run_id)
    if run_session is None:
        return None
    return RunSummaryResponse.from_run_session(run_session)


def load_event_page(
    sqlite_path: str,
    run_id: str,
    *,
    branch_id: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> RunEventPageResponse:
    store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path))
    events = store.query_events(run_id=run_id, branch_id=branch_id)
    offset = _parse_non_negative_int(cursor, field="cursor", default=0)
    page_limit = _parse_positive_int(limit, field="limit")
    items = events[offset : offset + page_limit]
    next_cursor = str(offset + page_limit) if offset + page_limit < len(events) else None
    return RunEventPageResponse(run_id=run_id, items=items, next_cursor=next_cursor, limit=page_limit)


def load_branch_page(sqlite_path: str, run_id: str) -> BranchListResponse:
    branch_store = BranchTraceStore(BranchTraceStoreConfig(sqlite_path=sqlite_path))
    branch_heads = branch_store.get_branch_heads(run_id)
    return BranchListResponse(
        run_id=run_id,
        items=[
            BranchSummary(branch_id=branch_id, head_node_id=head_node_id)
            for branch_id, head_node_id in sorted(branch_heads.items())
        ],
    )


def load_artifact_page(
    sqlite_path: str,
    workspace_root: str,
    artifact_root: str,
    run_id: str,
    *,
    branch_id: str | None = None,
) -> ArtifactListResponse:
    if branch_id is None:
        paths = _list_paths_for_roots(
            [
                Path(workspace_root) / run_id,
                Path(artifact_root) / run_id,
            ]
        )
        return ArtifactListResponse(
            run_id=run_id,
            items=[ArtifactDescriptor(path=path) for path in paths],
        )

    branch_store = BranchTraceStore(BranchTraceStoreConfig(sqlite_path=sqlite_path))
    descriptors = {}
    for node in branch_store.query_nodes(run_id=run_id, branch_id=branch_id):
        workspace_path = Path(node.workspace_ref)
        for path in _list_paths_for_roots([workspace_path]):
            descriptors[path] = ArtifactDescriptor(path=path, branch_id=branch_id)
        try:
            artifact_paths = json.loads(node.result_ref) if node.result_ref else []
        except json.JSONDecodeError:
            artifact_paths = []
        if isinstance(artifact_paths, list):
            for artifact_path in artifact_paths:
                path = str(artifact_path)
                if Path(path).exists():
                    descriptors[path] = ArtifactDescriptor(path=path, branch_id=branch_id)
    return ArtifactListResponse(
        run_id=run_id,
        items=[descriptors[key] for key in sorted(descriptors.keys())],
    )


def _list_paths_for_roots(roots: list[Path]) -> list[str]:
    paths = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                paths.add(str(path))
    return sorted(paths)


def _parse_non_negative_int(value: object, *, field: str, default: int) -> int:
    raw_value = default if value is None else value
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ServiceContractError(
            code=ErrorCode.INVALID_REQUEST,
            message=f"{field} must be an integer >= 0",
            field=field,
        ) from exc
    if parsed < 0:
        raise ServiceContractError(
            code=ErrorCode.INVALID_REQUEST,
            message=f"{field} must be >= 0",
            field=field,
        )
    return parsed


def _parse_positive_int(value: object, *, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ServiceContractError(
            code=ErrorCode.INVALID_REQUEST,
            message=f"{field} must be an integer > 0",
            field=field,
        ) from exc
    if parsed <= 0:
        raise ServiceContractError(
            code=ErrorCode.INVALID_REQUEST,
            message=f"{field} must be > 0",
            field=field,
        )
    return parsed
