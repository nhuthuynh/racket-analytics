"""IT-02-05 (ST-026..ST-037; NFR-051, FR-002): the BOLA matrix covers every Sprint 2 route.

The full matrix lives in the regression suite (``tests/regression/test_bola_matrix.py``, never
deleted). This IT runs the Sprint 2 rows on committed data (the API driver, as the browser
would reach it) and checks the inventory: every route under ``/matches/{match_id}/`` that the
app serves has a probe. Carlos gets the same 404 as for a missing resource; Ivy (positive
control) never gets a 404 or 405 on her own match.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from tests.regression.bola import MATCH_ID_ROUTES_02, MATRIX, RALLY_ID_ROUTES_02, id_routes
from tests.support import scorebook as sb
from tests.support.api import ApiDriver

ROUTES = [(m, t, k, "match") for (m, t), k in MATCH_ID_ROUTES_02.items()] + [
    (m, t, k, "rally") for (m, t), k in RALLY_ID_ROUTES_02.items()
]


@pytest.fixture
def ivy_match(api: ApiDriver) -> dict[str, str]:
    match_id = sb.ready_tagged_match(api, "ivy", title="IT-02-05")
    rows = api.run(sb.sheet(api.as_user("ivy"), match_id)).json()["rows"]
    api.as_user("carlos")
    return {"match": match_id, "rally": rows[0]["rally_id"]}


def _strip(response: Any) -> tuple[int, Any]:
    body = response.json() if response.content else None
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body["error"].pop("support_ref", None)
    return response.status_code, body


@pytest.mark.parametrize(
    ("method", "template", "kwargs", "kind"), ROUTES, ids=[f"{m} {t}" for m, t, _, _ in ROUTES]
)
def test_it_02_05_carlos_gets_the_missing_resource_404_on_every_sprint_2_route(
    api: ApiDriver, ivy_match: dict[str, str], method: str, template: str, kwargs: Any, kind: str
) -> None:
    own = template.format(match_id=ivy_match["match"], rally_id=ivy_match["rally"])
    missing = template.format(match_id=uuid.uuid4(), rally_id=ivy_match["rally"])
    owner = api.request("ivy", method, own, **kwargs())
    attacker = api.request("carlos", method, own, **kwargs())
    absent = api.request("carlos", method, missing, **kwargs())
    assert owner.status_code not in (404, 405), f"positive control: {owner.status_code}"
    assert attacker.status_code == 404, attacker.text
    assert _strip(attacker) == _strip(absent)
    if kind == "rally":
        other_rally = template.format(match_id=ivy_match["match"], rally_id=uuid.uuid4())
        assert api.request("ivy", method, other_rally, **kwargs()).status_code in (404, 409)


def test_it_02_05_every_match_scoped_route_has_a_probe(api: ApiDriver) -> None:
    served = {k for k in id_routes(api.app) if k[1].startswith("/matches/{match_id}/")}
    assert served, "inventory is empty (BE-QA-01)"
    assert served - set(MATRIX) == set(), sorted(served - set(MATRIX))
