# ADR 002: Streamlit for Trace Inspection UI

## Status
Accepted

## Context
The platform generates extensive execution traces during the R&D process, including LLM prompts, tool outputs, and workspace changes. Developers need a UI tool to inspect these traces for debugging and evaluation.

The options considered were:
1.  **React/Vue.js**: Full control over UI, but requires specialized frontend skills and significantly more development time.
2.  **Gradio**: Good for ML demos, but less flexible for complex data visualizations.
3.  **Streamlit**: Python-native framework that allows rapid prototyping of data-centric UIs without writing JavaScript.

## Decision
We chose **Streamlit** to build the trace inspection and monitoring UI.

The UI is implemented in `ui/trace_ui.py`. It integrates with the SQLite storage to fetch session metadata and event streams, providing a high-level overview and detailed drill-down views of the agent's actions.

## Consequences
- **Rapid Prototyping**: New UI features can be added in hours rather than days by developers who primarily work in Python.
- **Team Consistency**: The team already uses Python for the core agent logic, so Streamlit fits into the existing skill set.
- **Deployment**: Streamlit apps are easy to deploy as standalone services alongside the core agent engine.
- **Limited Interactivity**: Streamlit has a unique execution model (re-running the script on every interaction), which can lead to performance issues or state management complexity for highly interactive UIs.
- **Read-Only Focus**: The current UI is primarily designed as a viewer/inspector. More complex interactive management tools might eventually require a more traditional frontend framework.
