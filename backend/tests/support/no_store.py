"""Every authenticated GET route and how to call it as its owner (ST-078d; NFR-067.1).

The GET inventory is ``bola.all_routes``: a route is public only if it is listed in ``PUBLIC_GETS``
with a reason; every other GET route is authenticated and must say ``Cache-Control: no-store``.
``fill`` turns a route template into the owner's URL from the resources Ivy creates in the IT.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from tests.regression.bola import all_routes
from tests.support import scorebook
from tests.support.stats import WORKED_EXAMPLE

# GET routes served without a session. Each needs a reason; the IT checks each answers anonymously.
PUBLIC_GETS: dict[str, str] = {
    "/healthz": "liveness probe (ST-005)",
    "/readyz": "readiness probe (ST-005)",
    "/config/public": "feature flags the web reads before sign-in (ST-067)",
    "/dev/users": "dev-identity user list, routed only when DEV_IDENTITY is on (api-sprint-00 §2)",
    "/docs": "OpenAPI UI, routed only in dev and test",
    "/docs/oauth2-redirect": "OpenAPI UI helper, routed only in dev and test",
    "/redoc": "OpenAPI UI, routed only in dev and test",
    "/openapi.json": "OpenAPI document, routed only in dev and test",
}
# Query parameters a route needs before it reaches its handler.
QUERY: dict[str, Mapping[str, str]] = {
    "/matches/{match_id}/stats/{metric_id}/evidence": {"side": "A", "limit": "10"},
}


PLAN_PREFERENCES = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}


async def seed_resources(ivy: httpx.AsyncClient, title: str) -> dict[str, str]:
    """Ivy's tagged match (video received, the worked example tagged) and her plan, so every
    id route and ``/me/plan`` reach their handler."""
    tagged = await scorebook.create_doubles(ivy, title)
    await scorebook.receive_video(ivy, tagged)
    await scorebook.start_game(ivy, tagged)
    tags = await scorebook.tag_all(ivy, tagged, list(WORKED_EXAMPLE))
    plan = await ivy.post("/me/plan", json=PLAN_PREFERENCES)
    assert plan.status_code == 201, plan.text
    return {"tagged": tagged, "rally": str(tags[0].json()[scorebook.tagcontract.RALLY_ID_KEY])}


def authenticated_gets(app: Any) -> list[str]:
    """Path templates of every GET route of ``app`` that is not in ``PUBLIC_GETS``."""
    return sorted(path for method, path in all_routes(app) if method == "GET"
                  and path not in PUBLIC_GETS)  # fmt: skip


def fill(template: str, resources: Mapping[str, str]) -> str:
    """The owner's URL for ``template``: her tagged match (video received, one rally)."""
    return template.format(
        match_id=resources["tagged"], rally_id=resources["rally"], metric_id="AN-01"
    )


def cache_control(headers: Any) -> list[str]:
    """Every ``Cache-Control`` value the response sent (a duplicate header is a finding too)."""
    return list(headers.get_list("cache-control"))


def without_no_store(answers: Mapping[str, httpx.Response]) -> list[str]:
    """``"<route>: <values>"`` for every answer whose Cache-Control is not exactly one
    ``no-store``; empty when NFR-067.1 holds."""
    return [
        f"{route}: {cache_control(r.headers)}"
        for route, r in answers.items()
        if cache_control(r.headers) != ["no-store"]
    ]
