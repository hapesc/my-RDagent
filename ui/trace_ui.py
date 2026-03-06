"""Branch-aware Streamlit trace UI built on shared V1 DTO helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.control_plane_client import ControlPlaneClient
from app.control_plane import build_control_plane_app
from app.fastapi_compat import TestClient
from app.query_services import (
    load_artifact_page as query_load_artifact_page,
    load_branch_page as query_load_branch_page,
    load_event_page as query_load_event_page,
    load_run_summary as query_load_run_summary,
)
from app.runtime import build_runtime
from core.storage import SQLiteMetadataStore, SQLiteStoreConfig
from data_models import Event
from service_contracts import (
    ArtifactListResponse,
    BranchListResponse,
    RunControlResponse,
    RunEventPageResponse,
    RunSummaryResponse,
    ScenarioManifest,
)
from trace_store import TraceTimelineView


def load_run_ids(sqlite_path: str) -> List[str]:
    store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path))
    return [run.run_id for run in store.list_runs()]


def build_local_control_plane_client() -> ControlPlaneClient:
    return ControlPlaneClient(TestClient(build_control_plane_app()))


def load_event_page(
    sqlite_path: str,
    run_id: str,
    branch_id: Optional[str] = None,
    *,
    cursor: Optional[str] = None,
    limit: int = 50,
) -> RunEventPageResponse:
    return query_load_event_page(
        sqlite_path,
        run_id,
        branch_id=branch_id,
        cursor=cursor,
        limit=limit,
    )


def load_events(
    sqlite_path: str,
    run_id: str,
    branch_id: Optional[str] = None,
    *,
    page_limit: int = 50,
) -> List[Event]:
    events: List[Event] = []
    cursor: Optional[str] = None
    while True:
        page = load_event_page(
            sqlite_path=sqlite_path,
            run_id=run_id,
            branch_id=branch_id,
            cursor=cursor,
            limit=page_limit,
        )
        events.extend(page.items)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    return events


def load_run_summary(sqlite_path: str, run_id: str) -> Optional[RunSummaryResponse]:
    return query_load_run_summary(sqlite_path, run_id)


def load_branches(sqlite_path: str, run_id: str) -> BranchListResponse:
    return query_load_branch_page(sqlite_path, run_id)


def load_scenario_manifests() -> List[ScenarioManifest]:
    return build_runtime().plugin_registry.list_manifests()


def build_timeline_rows(events: List[Event]) -> List[Dict[str, Any]]:
    return TraceTimelineView().build_rows(events)


def load_artifact_manifest(
    sqlite_path: str,
    workspace_root: str,
    artifact_root: str,
    run_id: str,
    branch_id: Optional[str] = None,
) -> ArtifactListResponse:
    return query_load_artifact_page(
        sqlite_path,
        workspace_root,
        artifact_root,
        run_id,
        branch_id=branch_id,
    )


def list_artifacts(
    sqlite_path: str,
    workspace_root: str,
    artifact_root: str,
    run_id: str,
    branch_id: Optional[str] = None,
) -> List[str]:
    return [
        descriptor.path
        for descriptor in load_artifact_manifest(
            sqlite_path=sqlite_path,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
            run_id=run_id,
            branch_id=branch_id,
        ).items
    ]


def perform_control_action(client: Any, run_id: str, action: str) -> RunControlResponse:
    if action not in {"pause", "resume", "stop"}:
        raise ValueError(f"unsupported control action: {action}")
    if hasattr(client, f"{action}_run"):
        return getattr(client, f"{action}_run")(run_id)
    response = client.post(f"/runs/{run_id}/{action}", json={})
    payload = response.json()
    if response.status_code >= 400:
        error_message = payload.get("error", {}).get("message", "control action failed")
        raise RuntimeError(error_message)
    return RunControlResponse(
        run_id=str(payload["run_id"]),
        action=str(payload["action"]),
        status=str(payload["status"]),
        message=str(payload.get("message", "")),
    )


def build_branch_compare_summary(
    sqlite_path: str,
    workspace_root: str,
    artifact_root: str,
    run_id: str,
    selected_branch_id: Optional[str],
    *,
    baseline_branch_id: str = "main",
) -> Dict[str, Any]:
    branches = load_branches(sqlite_path, run_id)
    branch_heads = {item.branch_id: item.head_node_id for item in branches.items}
    if not selected_branch_id:
        return {"message": "select a branch to compare"}
    if selected_branch_id == baseline_branch_id:
        return {"message": "selected branch already matches baseline"}
    if baseline_branch_id not in branch_heads or selected_branch_id not in branch_heads:
        return {"message": "comparison unavailable for selected branches"}

    baseline_events = load_events(sqlite_path, run_id, baseline_branch_id, page_limit=25)
    selected_events = load_events(sqlite_path, run_id, selected_branch_id, page_limit=25)
    baseline_artifacts = load_artifact_manifest(
        sqlite_path,
        workspace_root,
        artifact_root,
        run_id,
        branch_id=baseline_branch_id,
    )
    selected_artifacts = load_artifact_manifest(
        sqlite_path,
        workspace_root,
        artifact_root,
        run_id,
        branch_id=selected_branch_id,
    )
    return {
        "baseline_branch_id": baseline_branch_id,
        "baseline_head_node_id": branch_heads[baseline_branch_id],
        "baseline_event_count": len(baseline_events),
        "baseline_artifact_count": len(baseline_artifacts.items),
        "selected_branch_id": selected_branch_id,
        "selected_head_node_id": branch_heads[selected_branch_id],
        "selected_event_count": len(selected_events),
        "selected_artifact_count": len(selected_artifacts.items),
    }


def _extract_metrics(artifact_paths: List[str]) -> Dict[str, Any]:
    for path in artifact_paths:
        if path.endswith("metrics.json"):
            try:
                return json.loads(Path(path).read_text(encoding="utf-8"))
            except Exception:
                return {"error": "failed to parse metrics.json"}
    return {}


def run_app() -> None:
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("streamlit is required for UI: pip install streamlit") from exc

    st.set_page_config(page_title="AgentRD Trace UI", layout="wide")
    st.title("AgentRD Trace UI")

    @st.cache_resource
    def _client() -> ControlPlaneClient:
        return build_local_control_plane_client()

    client = _client()

    sqlite_path = st.sidebar.text_input(
        "SQLite Path",
        value=os.environ.get("AGENTRD_SQLITE_PATH", "/tmp/rd_agent.sqlite3"),
    )
    workspace_root = st.sidebar.text_input(
        "Workspace Root",
        value=os.environ.get("AGENTRD_WORKSPACE_ROOT", "/tmp/rd_agent_workspace"),
    )
    artifact_root = st.sidebar.text_input(
        "Artifact Root",
        value=os.environ.get("AGENTRD_ARTIFACT_ROOT", "/tmp/rd_agent_artifacts"),
    )
    manifests = load_scenario_manifests()
    if manifests:
        with st.sidebar.expander("Scenario Manifests", expanded=False):
            st.json([manifest.to_dict() for manifest in manifests])

    run_ids = load_run_ids(sqlite_path)
    if not run_ids:
        st.info("No runs found.")
        return

    run_id = st.sidebar.selectbox("Run ID", options=run_ids)
    run_summary = load_run_summary(sqlite_path, run_id)
    branches = load_branches(sqlite_path, run_id)
    branch_options = ["all"] + [item.branch_id for item in branches.items]
    selected_branch = st.sidebar.selectbox("Branch", options=branch_options, index=0)
    branch_id = None if selected_branch == "all" else selected_branch

    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
    refresh_sec = st.sidebar.slider("Refresh Interval (sec)", min_value=2, max_value=30, value=5)
    page_limit = st.sidebar.slider("Event Page Size", min_value=10, max_value=100, value=25, step=5)
    if auto_refresh:
        st.markdown(f"<meta http-equiv='refresh' content='{refresh_sec}'>", unsafe_allow_html=True)

    events = load_events(
        sqlite_path=sqlite_path,
        run_id=run_id,
        branch_id=branch_id,
        page_limit=page_limit,
    )
    rows = build_timeline_rows(events)

    st.subheader("Run Overview")
    if run_summary is not None:
        st.json(run_summary.to_dict())

    control_columns = st.columns(3)
    control_actions = [("Pause", "pause"), ("Resume", "resume"), ("Stop", "stop")]
    for column, (label, action) in zip(control_columns, control_actions):
        with column:
            if st.button(label):
                try:
                    st.session_state["control_action"] = perform_control_action(client, run_id, action).to_dict()
                except RuntimeError as exc:
                    st.session_state["control_action"] = {"error": str(exc)}
    if "control_action" in st.session_state:
        st.caption("Control Action")
        st.json(st.session_state["control_action"])

    st.subheader("Branch Heads")
    st.dataframe([item.to_dict() for item in branches.items], use_container_width=True)

    st.subheader("Timeline")
    st.dataframe(rows, use_container_width=True)

    event_ids = [event.event_id for event in events]
    selected_event = None
    if event_ids:
        selected_event_id = st.selectbox("Event Detail", options=event_ids, index=len(event_ids) - 1)
        selected_event = next(event for event in events if event.event_id == selected_event_id)

    left, right = st.columns(2)
    with left:
        st.subheader("Event Payload")
        if selected_event is None:
            st.warning("No events for selected run/branch.")
        else:
            st.json(selected_event.to_dict())

    artifact_manifest = load_artifact_manifest(
        sqlite_path=sqlite_path,
        workspace_root=workspace_root,
        artifact_root=artifact_root,
        run_id=run_id,
        branch_id=branch_id,
    )
    artifacts = [item.path for item in artifact_manifest.items]
    metrics = _extract_metrics(artifacts)

    with right:
        st.subheader("Artifacts")
        st.dataframe([item.to_dict() for item in artifact_manifest.items], use_container_width=True)
        st.subheader("Metrics")
        st.json(metrics if metrics else {"message": "metrics not found"})

    st.subheader("Compare Summary")
    st.json(
        build_branch_compare_summary(
            sqlite_path=sqlite_path,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
            run_id=run_id,
            selected_branch_id=branch_id,
        )
    )


if __name__ == "__main__":
    run_app()
