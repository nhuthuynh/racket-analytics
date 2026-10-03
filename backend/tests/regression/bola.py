"""BOLA matrix and endpoint inventory (testing-strategy §5; NFR-051; AQS/SEC-09, AQS/SEC-03).

Every route whose path takes a parameter must have a matrix entry, or an exemption with a
reason. ``uncovered_routes`` is what makes "a new route without BOLA coverage" fail.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from tests.support import contract

PATH_PARAM = re.compile(r"\{[^}]+\}")
IGNORED_METHODS = frozenset({"OPTIONS"})

RouteKey = tuple[str, str]  # (METHOD, path template)


@dataclass(frozen=True)
class Probe:
    """How to call one route as an attacker: given the target URL, return request kwargs."""

    method: str
    template: str
    resource: str  # which of Ivy's resources the route addresses: "match" | "upload"
    kwargs: Callable[[], Mapping[str, Any]] = lambda: {}


def _tus(**extra: str) -> Callable[[], Mapping[str, Any]]:
    return lambda: {"headers": {"Tus-Resumable": contract.TUS_VERSION, **extra}}


_PROBES = [
    Probe("GET", contract.MATCH, "match"),
    Probe("GET", contract.MATCH_MEDIA, "match"),
    Probe("POST", contract.UPLOAD_CREATE, "match", _tus(**{"Upload-Length": "10"})),
    Probe("HEAD", contract.UPLOAD_RESOURCE, "upload", _tus()),
    Probe(
        "PATCH",
        contract.UPLOAD_RESOURCE,
        "upload",
        lambda: {
            "headers": {
                "Tus-Resumable": contract.TUS_VERSION,
                "Upload-Offset": "0",
                "Content-Type": "application/offset+octet-stream",
            },
            "content": b"x",
        },
    ),
]
MATRIX: dict[RouteKey, Probe] = {(p.method, p.template): p for p in _PROBES}

# Routes with a path parameter that is not an owned resource ID. Each needs a reason.
EXEMPT: dict[RouteKey, str] = {}


def id_routes(app: Any) -> set[RouteKey]:
    """(METHOD, path) for every route of ``app`` whose path takes a parameter."""
    keys: set[RouteKey] = set()
    for route in getattr(app, "routes", []):
        path = getattr(route, "path", "")
        methods: Iterable[str] = getattr(route, "methods", None) or ()
        if not PATH_PARAM.search(path):
            continue
        for method in methods:
            if method not in IGNORED_METHODS:
                keys.add((method.upper(), path))
    return keys


def uncovered_routes(
    app: Any,
    matrix: Mapping[RouteKey, object] | None = None,
    exempt: Mapping[RouteKey, str] | None = None,
) -> list[str]:
    covered = set(MATRIX if matrix is None else matrix) | set(EXEMPT if exempt is None else exempt)
    return sorted(f"{m} {p}" for (m, p) in id_routes(app) - covered)
