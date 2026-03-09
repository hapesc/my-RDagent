"""Small FastAPI compatibility layer for environments without the dependency."""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from dataclasses import dataclass
from re import Pattern
from types import SimpleNamespace
from typing import Any

try:  # pragma: no cover - exercised only when real FastAPI is available
    from fastapi import FastAPI as _FastAPI
    from fastapi import HTTPException as _HTTPException
    from fastapi import Query as _Query

    FastAPI = _FastAPI
    HTTPException = _HTTPException
    Query = _Query
    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - covered through local compatibility tests
    FASTAPI_AVAILABLE = False

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: Any) -> None:
            super().__init__(str(detail))
            self.status_code = status_code
            self.detail = detail

    def Query(default: Any = None, **_kwargs: Any) -> Any:
        return default

    @dataclass
    class _Route:
        method: str
        path: str
        regex: Pattern[str]
        param_names: list[str]
        handler: Callable[..., Any]

    class FastAPI:
        def __init__(self, title: str = "app") -> None:
            self.title = title
            self.state = SimpleNamespace()
            self._routes: list[_Route] = []

        def get(self, path: str, **_kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            return self._register("GET", path)

        def post(self, path: str, **_kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            return self._register("POST", path)

        def _register(self, method: str, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
                regex, param_names = self._compile_path(path)
                self._routes.append(
                    _Route(
                        method=method,
                        path=path,
                        regex=regex,
                        param_names=param_names,
                        handler=handler,
                    )
                )
                return handler

            return decorator

        def _compile_path(self, path: str) -> tuple[Pattern[str], list[str]]:
            param_names = re.findall(r"{([^}]+)}", path)
            pattern = "^" + re.sub(r"{([^}]+)}", r"(?P<\1>[^/]+)", path) + "$"
            return re.compile(pattern), param_names

        def handle_request(
            self,
            method: str,
            path: str,
            json_body: dict[str, Any] | None = None,
            query_params: dict[str, Any] | None = None,
        ) -> tuple[int, Any]:
            for route in self._routes:
                if route.method != method.upper():
                    continue
                match = route.regex.match(path)
                if match is None:
                    continue
                try:
                    payload = self._invoke(route.handler, match.groupdict(), json_body or {}, query_params or {})
                except HTTPException as exc:
                    return exc.status_code, exc.detail
                return 200, payload
            return 404, {"error": {"code": "not_found", "message": f"route not found: {method} {path}"}}

        def _invoke(
            self,
            handler: Callable[..., Any],
            path_params: dict[str, Any],
            body: dict[str, Any],
            query: dict[str, Any],
        ) -> Any:
            signature = inspect.signature(handler)
            kwargs: dict[str, Any] = {}
            for name, parameter in signature.parameters.items():
                if name in path_params:
                    kwargs[name] = path_params[name]
                elif name in query:
                    kwargs[name] = query[name]
                elif name in {"payload", "request", "body"}:
                    kwargs[name] = body
                elif name in body:
                    kwargs[name] = body[name]
                elif parameter.default is not inspect._empty:
                    kwargs[name] = parameter.default
            return handler(**kwargs)


class status:
    HTTP_200_OK = 200
    HTTP_201_CREATED = 201
    HTTP_400_BAD_REQUEST = 400
    HTTP_404_NOT_FOUND = 404
    HTTP_409_CONFLICT = 409
    HTTP_500_INTERNAL_SERVER_ERROR = 500


class TestClient:
    """Very small test client for the compatibility app."""

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    def get(self, path: str, params: dict[str, Any] | None = None):
        return _Response(*self._app.handle_request("GET", path, query_params=params))

    def post(self, path: str, json: dict[str, Any] | None = None):
        return _Response(*self._app.handle_request("POST", path, json_body=json))


@dataclass
class _Response:
    status_code: int
    _payload: Any

    def json(self) -> Any:
        return self._payload
