"""IT-03-12 (QA-FUZZ-3; testing-strategy rule L11; NFR-023, NFR-058): the Sprint 3 JSON fields.

Rule L11 on every new JSON string field: the delete confirmations (match and account) and the
Full Tag label bodies (event type, hitter, rally outcome fields). Hypothesis text holding at
least one control (Cc), surrogate (Cs) or line/paragraph separator, plus the named NUL,
lone-surrogate and U+2028 cases, and any JSON value (rule 9): always a 4xx, never a 5xx, and no
row written (deleting nothing is the "no row written" of a DELETE). The consent record is
written by the labeller-admin CLI, not a JSON route, so it is not in this file.

Concurrency for the new limits (NFR-058): a DELETE racing a tag on one match ends in one
consistent outcome: the delete always wins (202) and nothing of the match is readable afterwards,
while the tag ends as 201 (it landed first), 404 or 409; parallel purge passes are in IT-03-07.

Generators and the "still bad where the server reads it" filter come from IT-02-10, so both
files test the same input domain. Written red first, one ``red_until`` per row naming the story
that row really waits on (review round 1, F1): the match delete rows and the race wait on ST-050
(``DELETE /matches/{id}``), the account delete rows on ST-051 (``DELETE /me``), the label rows on
ST-052 (the labeller seam and the label route). Each story removes the markers of its own rows. A
DELETE answered 405 (the route is not built yet) is never counted as an L11 refusal.

ST-050a (TCR row in docs/sprints/03/decisions/ST-050a.md): the match delete rows and the race
pass and join the per-PR gate; their ``delete_match`` marker is removed (a row with no entry in
``WAITS_ON`` carries no marker).

ST-051-API (TCR row in docs/sprints/03/decisions/ST-051-API.md): the account delete rows pass and
join the per-PR gate; their ``delete_account`` entry is removed from ``WAITS_ON``.

ST-052c (TCR row in docs/sprints/03/decisions/ST-052c.md): the label rows and their positive
control pass and join the per-PR gate; their ``label`` entry is removed from ``WAITS_ON``.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import given

from tests.integration.test_it_02_10_json_string_fuzz import ANY_JSON, SETTINGS, bad_text
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

WAITS_ON: dict[str, Any] = {}

OUTCOME: dict[str, Any] = {"ending": "winner", "winning_side": "B", "responsible_player": "B1"}
RALLY_EVENT: dict[str, Any] = {
    "type": "rally",
    "start_frame": 1800,
    "end_frame": 1900,
    "outcome": OUTCOME,
}
Builder = Callable[[Any], Any]
NOT_BUILT = 405  # method_not_allowed: the route of the row's story is not built yet
# field -> (route kind, body builder, valid base value)
FIELDS: dict[str, tuple[str, Builder, str]] = {
    "delete_match.confirm": ("delete_match", lambda v: {"confirm": v}, "delete"),
    "delete_account.confirm": ("delete_account", lambda v: {"confirm": v}, "delete"),
    "label.type": ("label", lambda v: {"type": v, "frame": 10, "hitter": "B1"}, "hit"),
    "label.hitter": ("label", lambda v: {"type": "hit", "frame": 10, "hitter": v}, "B1"),
    "label.outcome.ending": (
        "label",
        lambda v: {**RALLY_EVENT, "outcome": {**OUTCOME, "ending": v}},
        "winner",
    ),
    "label.outcome.winning_side": (
        "label",
        lambda v: {**RALLY_EVENT, "outcome": {**OUTCOME, "winning_side": v}},
        "B",
    ),
    "label.outcome.responsible_player": (
        "label",
        lambda v: {**RALLY_EVENT, "outcome": {**OUTCOME, "responsible_player": v}},
        "B1",
    ),
}


def _rows(*extra: tuple[Any, str]) -> list[Any]:
    """One param per field (times each ``(value, id)`` in ``extra``), each carrying the marker
    of the story its route waits on."""
    out = []
    for field in sorted(FIELDS):
        mark = WAITS_ON.get(FIELDS[field][0], [])
        if not extra:
            out.append(pytest.param(field, marks=mark, id=field))
        out += [pytest.param(field, v, marks=mark, id=f"{field}-{i}") for v, i in extra]
    return out


class Target:
    """Ivy's match (the delete rows); for a label row also Dana's labeller match, probed and with
    consent, so a label body reaches the L11 check and not 409 ``match_not_ready``."""

    def __init__(self, api: ApiDriver, engine: Any, kind: str) -> None:
        self.api, self.engine = api, engine
        client = api.as_user("ivy")
        self.match_id = api.run(sb.create_doubles(client, "IT-03-12"))
        api.run(sb.receive_video(client, self.match_id))
        self.ivy = st.me_id(api, "ivy")
        self.ids = [self.match_id, self.ivy]
        self.label_match = ""
        if kind == "label":
            st.grant_labeller(api, "dana")
            self.label_match = api.run(sb.create_doubles(api.as_user("dana"), "IT-03-12 label"))
            api.run(sb.receive_video(api.as_user("dana"), self.label_match))
            st.probe_videos()
            st.record_consent(self.label_match)
            self.ids.append(self.label_match)
            # Positive control: the label routes are served and Dana's consented match opens;
            # an unserved route is a 404, which would count as an L11 refusal (vacuous pass).
            opened = st.fulltag(api, "dana", "label_match", match_id=self.label_match)
            assert opened.status_code == 200, f"positive control: {opened.status_code}"

    def snapshot(self) -> dict[str, int]:
        rows = st.rows_holding(self.engine, self.ids)
        return {**rows, **sb.row_counts(self.engine)}

    def send(self, kind: str, body: Any) -> Any:
        raw = json.dumps(body).encode()  # surrogates travel as \\uXXXX escapes
        headers = {"Content-Type": "application/json"}
        if kind == "delete_match":
            method, url = st.statscontract.path("delete_match", match_id=self.match_id)
            return self.api.request("ivy", method, url, content=raw, headers=headers)
        if kind == "delete_account":
            method, url = st.statscontract.path("delete_account")
            return self.api.request("ivy", method, url, content=raw, headers=headers)
        method, template = st.FULLTAG_ROUTES["label_events"]
        url = template.format(match_id=self.label_match)
        return self.api.request("dana", method, url, content=raw, headers=headers)


@pytest.fixture
def make_target(api: ApiDriver, committed_db: Any) -> Callable[[str], Target]:
    return lambda kind: Target(api, committed_db, kind)


def _built(kind: str, response: Any) -> None:
    """The refusal comes from the body check, not from a missing route or an unready match."""
    assert response.status_code != NOT_BUILT, f"{kind}: route not built yet ({response.text[:200]})"
    assert "match_not_ready" not in response.text, f"{kind}: refused before L11 ({response.text})"


def _refused(target: Target, kind: str, body: Any) -> None:
    before = target.snapshot()
    response = target.send(kind, body)
    _built(kind, response)
    assert 400 <= response.status_code < 500, (
        f"{kind}: {response.status_code} {response.text[:300]} for {json.dumps(body)[:200]}"
    )
    assert target.snapshot() == before, f"{kind}: a row was written or deleted"


def test_it_03_12_positive_control_the_valid_label_is_accepted(
    make_target: Callable[[str], Target],
) -> None:
    target = make_target("label")
    response = target.send("label", RALLY_EVENT)
    assert response.status_code in (200, 201), response.text


@pytest.mark.parametrize("field", _rows())
def test_it_03_12_bad_characters_are_a_4xx_and_change_nothing(
    make_target: Callable[[str], Target], field: str
) -> None:
    kind, build, base = FIELDS[field]
    target = make_target(kind)

    @SETTINGS
    @given(value=bad_text(base))
    def check(value: str) -> None:
        _refused(target, kind, build(value))

    check()


@pytest.mark.parametrize(
    ("field", "value"),
    _rows(
        ("\x00", "nul"),
        ("\ud800", "high-surrogate"),
        ("\udfff", "low-surrogate"),
        ("\u2028", "line-separator"),
        ("del\x00ete", "inner-nul"),
    ),
)
def test_it_03_12_named_characters_in_every_field(
    make_target: Callable[[str], Target], field: str, value: str
) -> None:
    kind, build, _ = FIELDS[field]
    target = make_target(kind)
    _refused(target, kind, build(value))


@pytest.mark.parametrize("field", _rows())
def test_it_03_12_any_json_value_is_never_a_5xx(
    make_target: Callable[[str], Target], field: str
) -> None:
    kind, build, base = FIELDS[field]
    target = make_target(kind)

    @SETTINGS
    @given(value=ANY_JSON)
    def check(value: Any) -> None:
        if value == base:
            return  # the valid value would really delete; the positive controls cover it
        response = target.send(kind, build(value))
        _built(kind, response)
        assert response.status_code < 500, f"{field}: {response.status_code} {response.text[:300]}"

    check()


def test_it_03_12_delete_racing_a_tag_ends_in_one_consistent_outcome(api: ApiDriver) -> None:
    match_id = sb.ready_match(api, "ivy", "IT-03-12 race")
    client = api.as_user("ivy")
    version = api.run(sb.version_of(client, match_id))
    tag_method, tag_url = sb.path("tag", match_id=match_id)
    del_method, del_url = st.statscontract.path("delete_match", match_id=match_id)

    async def race() -> tuple[int, int]:
        tagged, deleted = await asyncio.gather(
            client.request(
                tag_method,
                tag_url,
                json=st.WORKED_EXAMPLE[0],
                headers={sb.tagcontract.VERSION_HEADER: f'"{version}"'},
            ),
            client.request(del_method, del_url, json=st.statscontract.CONFIRM_BODY),
        )
        return tagged.status_code, deleted.status_code

    tag_code, delete_code = api.run(race())
    assert tag_code < 500, tag_code
    assert delete_code < 500, delete_code
    assert delete_code in st.statscontract.DELETE_OK, delete_code
    assert tag_code in (201, 404, 409), tag_code
    reads = (sb.path("sheet", match_id=match_id), st.statscontract.path("stats", match_id=match_id))
    for method, url in reads:
        assert api.request("ivy", method, url).status_code == 404, url
