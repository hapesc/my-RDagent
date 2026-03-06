# Task-22 Branch/Artifact Services and Branch-Aware UI

## Delivered

- Shared query layer in `app/query_services.py`:
  - `load_run_summary`
  - `load_event_page`
  - `load_branch_page`
  - `load_artifact_page`
- Control plane endpoints now read branch/event/artifact data through the shared DTO services.
- Streamlit UI helpers now consume the same DTO-shaped services and expose:
  - run overview
  - branch selector
  - branch head table
  - artifact browser
  - control actions
  - branch compare summary

## DTO reuse

`Task-22` keeps UI and control plane on the same contract surface:

- `RunSummaryResponse`
- `RunEventPageResponse`
- `BranchListResponse`
- `ArtifactListResponse`
- `RunControlResponse`

This keeps local Streamlit rendering aligned with the API shape without introducing a separate frontend-only model layer.

## Event polling model

UI event loading now loops over `RunEventPageResponse` using `cursor + limit` until `next_cursor` is empty. No SSE or WebSocket channel was added.

## Branch/artifact behavior

- run-wide artifact listing still aggregates workspace and artifact roots under the run id
- branch-aware artifact listing resolves from recorded `ExperimentNode.workspace_ref` and `result_ref`
- branch compare summary reports head node ids plus event/artifact counts for `main` vs selected branch
