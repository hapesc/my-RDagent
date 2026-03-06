"""Control plane application entrypoint."""

from __future__ import annotations

from .control_plane import build_control_plane_app

app = build_control_plane_app()
