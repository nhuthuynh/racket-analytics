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
    resource: str  # which of Ivy's resources the route addresses: "match" | "upload" | "rally"
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
# Sprint 2 scorebook routes (IT-02-05; BE-QA-01). A command without ``If-Match`` is a 409 for
# the owner (stale version), which is the positive control; the attacker must get the 404.
MATCH_ID_ROUTES_02 = {
    ("GET", "/matches/{match_id}/score-sheet"): lambda: {},
    ("POST", "/matches/{match_id}/games"): lambda: {
        "json": {"first_serving_side": "A", "ends_switched": False}
    },
    ("POST", "/matches/{match_id}/rallies"): lambda: {
        "json": {"start_ms": 0, "end_ms": 1000, "winning_side": "A", "ending": "winner"}
    },
    ("POST", "/matches/{match_id}/undo"): lambda: {},
    ("GET", "/matches/{match_id}/corrections"): lambda: {},
    ("GET", "/matches/{match_id}/video"): lambda: {},
}
RALLY_ID_ROUTES_02 = {
    ("PATCH", "/matches/{match_id}/rallies/{rally_id}"): lambda: {
        "json": {"field": "ending", "value": "winner"}
    },
    ("POST", "/matches/{match_id}/rallies/{rally_id}/resolution"): lambda: {
        "json": {"decision": "withdraw"}
    },
    ("GET", "/matches/{match_id}/rallies/{rally_id}/media"): lambda: {},
}
_PROBES += [Probe(m, t, "match", k) for (m, t), k in MATCH_ID_ROUTES_02.items()]
_PROBES += [Probe(m, t, "rally", k) for (m, t), k in RALLY_ID_ROUTES_02.items()]
MATRIX: dict[RouteKey, Probe] = {(p.method, p.template): p for p in _PROBES}

# Sprint 3 routes (IT-03-05; NFR-051), as ``scripts/measure/statscontract.py`` assumes them until
# api-sprint-03 (PE-1). Kept out of MATRIX while the routes do not exist, because the inventory's
# positive control requires every MATRIX route to be served. They do NOT count as covered in
# ``uncovered_routes``: when a route is served, the inventory reports it until QA moves its probe
# into MATRIX (TCR row), and IT-03-05 already probes it meanwhile.
# ``DELETE`` changes state, so IT-03-05 runs the owner's positive control last.
MATCH_ID_ROUTES_03 = {
    ("GET", "/matches/{match_id}/stats"): lambda: {},
    ("GET", "/matches/{match_id}/stats/{metric_id}/evidence"): lambda: {
        "params": {"side": "A", "limit": "10"}
    },
    ("DELETE", "/matches/{match_id}"): lambda: {"json": {"confirm": "delete"}},
}

# Routes with a path parameter that is not an owned resource ID. Each needs a reason.
EXEMPT: dict[RouteKey, str] = {}


def all_routes(app: Any) -> set[RouteKey]:
    """(METHOD, path) for every route of ``app``, including routes of included routers.

    FastAPI 0.142 keeps an included router as one ``_IncludedRouter`` entry without a ``path``
    (BE-QA-01); its routes sit on ``original_router`` with the include prefix in
    ``include_context.prefix``. Walked recursively, so a nested include is not missed."""
    keys: set[RouteKey] = set()

    def walk(routes: Iterable[Any], prefix: str) -> None:
        for route in routes:
            inner = getattr(route, "original_router", None)
            if inner is not None:
                context = getattr(route, "include_context", None)
                walk(inner.routes, prefix + (getattr(context, "prefix", "") or ""))
                continue
            path = getattr(route, "path", None)
            if path is None:
                raise AssertionError(f"route without a path in the inventory: {route!r}")
            for method in getattr(route, "methods", None) or ():
                keys.add((method.upper(), prefix + path))

    walk(getattr(app, "routes", []), "")
    return keys


def id_routes(app: Any) -> set[RouteKey]:
    """(METHOD, path) for every route of ``app`` whose path takes a parameter."""
    return {
        (method, path)
        for method, path in all_routes(app)
        if PATH_PARAM.search(path) and method not in IGNORED_METHODS
    }


def uncovered_routes(
    app: Any,
    matrix: Mapping[RouteKey, object] | None = None,
    exempt: Mapping[RouteKey, str] | None = None,
) -> list[str]:
    covered = set(MATRIX if matrix is None else matrix) | set(EXEMPT if exempt is None else exempt)
    return sorted(f"{m} {p}" for (m, p) in id_routes(app) - covered)
