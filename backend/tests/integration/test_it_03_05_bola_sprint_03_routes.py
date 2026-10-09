"""IT-03-05 (ST-046..ST-052; NFR-051, FR-002): the BOLA matrix covers every Sprint 3 route.

Carlos gets the same 404 as for a missing resource on Ivy's stats, evidence and delete routes,
and Ivy's match is unchanged after his DELETE. Ivy (positive control, run last because DELETE
changes state) never gets a 404 or 405 on her own match. The inventory check: every route
under ``/matches/{match_id}`` that the app serves, and every route of the label tool, has a
probe in ``tests/regression/bola.py`` (Sprint 2 table or ``MATCH_ID_ROUTES_03``).

``DELETE /me`` has no id in its path (it acts on the caller) and is covered by IT-03-08.
Written red first (QA-ACC-3): ``red_until`` ST-046 (the first Sprint 3 route).

The file-level marker became one marker per row (ST-046b, TCR row 2026-10-09 in
docs/sprints/03/decisions/ST-046b.md): the stats row passes and joins the per-PR gate.
The evidence row joins it with ST-047-API (TCR row 2026-10-09 in
docs/sprints/03/decisions/ST-047-API.md); the inventory test now waits on ST-050 only (DELETE is
not served yet).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from tests.regression.bola import MATCH_ID_ROUTES_03, MATRIX, id_routes
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

# One marker per row naming the story that serves the route (as IT-03-12 does): the stats row
# joins the gate with ST-046b, the evidence row with ST-047-API (TCR rows 2026-10-09 in
# docs/sprints/03/decisions/); DELETE stays red until ST-050, so the red-until report has no
# stale row.
WAITS_ON = {
    ("DELETE", "/matches/{match_id}"): pytest.mark.red_until(story="ST-050"),
}
ROUTES = [
    pytest.param(
        key, kwargs, id=f"{key[0]} {key[1]}", marks=[WAITS_ON[key]] if key in WAITS_ON else []
    )
    for key, kwargs in sorted(MATCH_ID_ROUTES_03.items())
]


def _strip(response: Any) -> tuple[int, Any]:
    body = response.json() if response.content else None
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body["error"].pop("support_ref", None)
    return response.status_code, body


@pytest.mark.parametrize(("key", "kwargs"), ROUTES)
def test_it_03_05_carlos_gets_the_missing_resource_404_on_every_sprint_3_route(
    api: ApiDriver, key: tuple[str, str], kwargs: Any
) -> None:
    method, template = key
    match_id = st.tagged_example(api, "ivy", "IT-03-05")
    api.as_user("carlos")
    own = template.format(match_id=match_id, metric_id="AN-01")
    missing = template.format(match_id=uuid.uuid4(), metric_id="AN-01")
    before = sb.sheet_body(api, "ivy", match_id)

    attacker = api.request("carlos", method, own, **kwargs())
    absent = api.request("carlos", method, missing, **kwargs())
    assert attacker.status_code == 404, attacker.text
    assert _strip(attacker) == _strip(absent)
    assert sb.sheet_body(api, "ivy", match_id) == before, "Carlos changed Ivy's match"

    owner = api.request("ivy", method, own, **kwargs())
    assert owner.status_code not in (404, 405), f"positive control: {owner.status_code}"


@pytest.mark.red_until(story="ST-050")  # the DELETE route is not served yet
def test_it_03_05_every_match_scoped_and_label_route_has_a_probe(api: ApiDriver) -> None:
    served = {
        k
        for k in id_routes(api.app)
        if k[1].startswith("/matches/{match_id}") or k[1].startswith("/label")
    }
    assert set(MATCH_ID_ROUTES_03) <= served, sorted(set(MATCH_ID_ROUTES_03) - served)
    probed = set(MATRIX) | set(MATCH_ID_ROUTES_03)
    assert served - probed == set(), sorted(served - probed)
