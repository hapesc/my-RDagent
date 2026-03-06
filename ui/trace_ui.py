"""Basic Streamlit trace UI for run timeline inspection."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.storage import SQLiteMetadataStore, SQLiteStoreConfig
from data_models import Event
from trace_store import TraceTimelineView


def load_run_ids(sqlite_path: str) -> List[str]:
    store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path))
    return [run.run_id for run in store.list_runs()]


def load_events(sqlite_path: str, run_id: str, branch_id: Optional[str] = None) -> List[Event]:
    store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path))
    return store.query_events(run_id=run_id, branch_id=branch_id)


def build_timeline_rows(events: List[Event]) -> List[Dict[str, Any]]:
    return TraceTimelineView().build_rows(events)


def list_artifacts(workspace_root: str, artifact_root: str, run_id: str) -> List[str]:
    paths: List[str] = []
    for root in [Path(workspace_root) / run_id, Path(artifact_root) / run_id]:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                paths.append(str(path))
    return sorted(set(paths))


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

    run_ids = load_run_ids(sqlite_path)
    if not run_ids:
        st.info("No runs found.")
        return

    run_id = st.sidebar.selectbox("Run ID", options=run_ids)
    branch_id = st.sidebar.text_input("Branch ID (optional)", value="").strip() or None

    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
    refresh_sec = st.sidebar.slider("Refresh Interval (sec)", min_value=2, max_value=30, value=5)
    if auto_refresh:
        st.markdown(f"<meta http-equiv='refresh' content='{refresh_sec}'>", unsafe_allow_html=True)

    events = load_events(sqlite_path=sqlite_path, run_id=run_id, branch_id=branch_id)
    rows = build_timeline_rows(events)

    st.subheader("Timeline")
    st.dataframe(rows, use_container_width=True)

    event_ids = [event.event_id for event in events]
    if not event_ids:
        st.warning("No events for selected run/branch.")
        return

    selected_event_id = st.selectbox("Event Detail", options=event_ids, index=len(event_ids) - 1)
    selected_event = next(event for event in events if event.event_id == selected_event_id)

    left, right = st.columns(2)
    with left:
        st.subheader("Event Payload")
        st.json(selected_event.to_dict())

    artifacts = list_artifacts(workspace_root=workspace_root, artifact_root=artifact_root, run_id=run_id)
    metrics = _extract_metrics(artifacts)

    with right:
        st.subheader("Artifacts")
        st.write(artifacts)
        st.subheader("Metrics")
        st.json(metrics if metrics else {"message": "metrics not found"})


if __name__ == "__main__":
    run_app()
