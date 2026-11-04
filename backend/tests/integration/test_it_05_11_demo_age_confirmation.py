"""IT-05-11 (QA-VERIFY04R5-01; DEMO-1.1; FR-003; api-sprint-04 §4): the service `make demo` uses.

API <-> DB, real Postgres, every R1 flag on (the ``flags_on`` fixture, kickoff 05 BE-2). A dev
user signed in on a flag-on app is refused with 403 ``age_confirmation_required`` until it
answers ``POST /me/age-confirmation`` with ``{"is_adult": true}``, exactly as a player does; a
second answer keeps the first ``age_confirmed_at`` (so `make demo` twice is idempotent). The
demo never writes the column itself. Negative cases first.
"""

from __future__ import annotations

import httpx

from tests.support import contract
from tests.support.age_gate import AGE_CONFIRMATION
from tests.support.api import sign_in
from tests.support.flags import FEATURE_FLAGS

DEMO_USER = "ivy"  # scripts/demo/demoplan.py DEMO_USER
ADULT = {"is_adult": True}  # scripts/demo/demoplan.py age_answer()


def _code(response: httpx.Response) -> str:
    return str(response.json()["error"]["code"])


# ------------------------------------------------------------------ negative cases first
async def test_it_05_11_flags_on_a_dev_user_is_refused_until_its_age_is_confirmed(
    flags_on_client: httpx.AsyncClient,
) -> None:
    await sign_in(flags_on_client, DEMO_USER)

    for path in (contract.ME, "/matches?limit=50", "/me/plan"):
        refused = await flags_on_client.get(path)
        assert refused.status_code == 403, (path, refused.text)
        assert _code(refused) == "age_confirmation_required", path


# ------------------------------------------------------------------ positive controls
async def test_it_05_11_flags_on_fixture_turns_every_r1_flag_on(
    flags_on: tuple[str, ...], flags_on_client: httpx.AsyncClient
) -> None:
    assert flags_on == FEATURE_FLAGS
    features = (await flags_on_client.get("/config/public")).json()["features"]
    assert features == dict.fromkeys(
        ("age_gate", "retention_setting", "training_consent", "quotas"), True
    )


async def test_it_05_11_flags_on_the_adult_answer_admits_the_dev_user_once(
    flags_on_client: httpx.AsyncClient,
) -> None:
    await sign_in(flags_on_client, DEMO_USER)

    first = await flags_on_client.post(AGE_CONFIRMATION, json=ADULT)
    assert first.status_code == 200, first.text
    me = await flags_on_client.get(contract.ME)
    assert me.status_code == 200, me.text
    assert first.json()["id"] == me.json()["id"]
    assert (await flags_on_client.get("/matches?limit=50")).status_code == 200

    again = await flags_on_client.post(AGE_CONFIRMATION, json=ADULT)
    assert again.status_code == 200, again.text
    assert again.json()["age_confirmed_at"] == first.json()["age_confirmed_at"]
