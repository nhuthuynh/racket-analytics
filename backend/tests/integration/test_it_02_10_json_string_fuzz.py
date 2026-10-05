"""IT-02-10 (QA-FUZZ, C-01; testing-strategy rule L11; NFR-041, NFR-058).

Every JSON string field of every JSON route (auth, matches, games, rallies, corrections,
resolutions), and every object key, gets Hypothesis-generated text holding at least one
control (Cc) or surrogate (Cs) character, NUL and the line/paragraph separators included.
The answer is a 4xx, never a 5xx, and no row is written anywhere.

A second property sends any JSON value (not only strings) in each field: still never a 5xx
(rule 9, "negative tests come from the input domain, not only from the contract text").

Bodies are sent as JSON text with ``\\u`` escapes, so a lone surrogate reaches the server the
way a browser or a script would send it. Positive controls (rule 8): each route accepts the
valid body in the same file.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

SETTINGS = settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)

# ------------------------------------------------------------------ strategies
BAD_CHAR = st.one_of(
    st.just("\x00"),
    st.sampled_from(["\u2028", "\u2029", "\x7f", "\x85", "\ud800", "\udfff"]),
    st.characters(categories=["Cc"]),
    st.characters(categories=["Cs"]),
)


@st.composite
def bad_text(draw: Any, base: str = "") -> str:
    """``base`` (or any text) with one bad character inside it, never only at an edge, so a
    trim cannot clean it, plus more bad characters anywhere."""
    if base and len(base) >= 2:
        i = draw(st.integers(1, len(base) - 1))
        text: str = base[:i] + draw(BAD_CHAR) + base[i:]
    else:
        inner = "x" + draw(BAD_CHAR) + "x"  # never at an edge, so a trim cannot remove it
        text = draw(st.text(max_size=12)) + inner + draw(st.text(max_size=12))
    extra = draw(st.lists(st.tuples(st.integers(0, len(text)), BAD_CHAR), max_size=3))
    for pos, ch in extra:
        text = text[:pos] + ch + text[pos:]
    return text


ANY_JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(max_size=8),
    lambda inner: (
        st.lists(inner, max_size=3) | st.dictionaries(st.text(max_size=4), inner, max_size=3)
    ),
    max_leaves=6,
)

# ------------------------------------------------------------------ the routes and their fields
VALID_TAG = {
    "start_ms": 50_000,
    "end_ms": 51_000,
    "winning_side": "A",
    "ending": "winner",
    "responsible_player": None,
    "fault_kind": None,
}


def match_body(**over: Any) -> dict[str, Any]:
    body = sb.doubles_body("Fuzz")
    body.update(over)
    return body


def participant_body(field: str, value: Any) -> dict[str, Any]:
    body = sb.doubles_body("Fuzz")
    body["participants"][1][field] = value
    return body


# name -> (user, route name or raw (method, url template), body builder, positive-control body)
Builder = Callable[[Any], Any]
FIELDS: dict[str, tuple[str, Builder, Any]] = {
    "auth.links.email": ("links", lambda v: {"email": v}, "ivy@example.com"),
    "auth.exchange.token": ("exchange", lambda v: {"token": v}, "x" * 43),
    "dev.sign_in.username": ("dev_sign_in", lambda v: {"username": v}, "ivy"),
    "matches.title": ("matches", lambda v: match_body(title=v), "Saturday"),
    "matches.format": ("matches", lambda v: match_body(format=v), "doubles"),
    "matches.scoring_system": ("matches", lambda v: match_body(scoring_system=v), "side_out"),
    "matches.played_on": ("matches", lambda v: match_body(played_on=v), "2026-10-01"),
    "matches.participants.slot": ("matches", lambda v: participant_body("slot", v), "A2"),
    "matches.participants.nickname": ("matches", lambda v: participant_body("nickname", v), "Di"),
    "games.first_serving_side": (
        "start_game", lambda v: {"first_serving_side": v, "ends_switched": False}, "A",
    ),
    "rallies.ending": ("tag", lambda v: {**VALID_TAG, "ending": v}, "winner"),
    "rallies.winning_side": ("tag", lambda v: {**VALID_TAG, "winning_side": v}, "A"),
    "rallies.responsible_player": ("tag", lambda v: {**VALID_TAG, "responsible_player": v}, "A1"),
    "rallies.fault_kind": (
        "tag", lambda v: {**VALID_TAG, "ending": "fault", "fault_kind": v}, None,
    ),
    "rallies.start_ms": ("tag", lambda v: {**VALID_TAG, "start_ms": v}, 50_000),
    "corrections.field": ("correct", lambda v: {"field": v, "value": "B"}, "winning_side"),
    "corrections.value.winning_side": (
        "correct", lambda v: {"field": "winning_side", "value": v}, "B",
    ),
    "corrections.value.ending": ("correct", lambda v: {"field": "ending", "value": v}, "winner"),
    "corrections.value.responsible_player": (
        "correct", lambda v: {"field": "responsible_player", "value": v}, None,
    ),
    "resolution.decision": ("resolution", lambda v: {"decision": v}, None),
}  # fmt: skip
AUTH_URLS = {"links": "/auth/links", "exchange": "/auth/exchange", "dev_sign_in": "/dev/sign-in"}
KEY_ROUTES = ("links", "exchange", "dev_sign_in", "matches", "start_game", "tag", "correct")


class Target:
    """One signed-in user with a received, started, tagged match; one per test function."""

    def __init__(self, api: ApiDriver, engine: Any) -> None:
        self.api = api
        self.engine = engine
        self.match_id = sb.ready_tagged_match(api, "ivy", title="IT-02-10")
        body = api.run(sb.sheet(api.as_user("ivy"), self.match_id)).json()
        self.rally_id = body["rows"][1]["rally_id"]  # rally 2: B, unforced error, no player

    def send(self, route: str, body: Any) -> Any:
        raw = json.dumps(body).encode()  # ensure_ascii: surrogates travel as \\uXXXX escapes
        headers = {"Content-Type": "application/json"}
        if route in ("links", "exchange", "dev_sign_in"):
            return self.api.request(
                "anonymous", "POST", AUTH_URLS[route], content=raw, headers=headers
            )
        if route == "matches":
            return self.api.request("ivy", "POST", "/matches", content=raw, headers=headers)
        client = self.api.as_user("ivy")
        version = self.api.run(sb.version_of(client, self.match_id))
        name = "correct" if route in ("correct",) else route
        if route == "resolution":
            res_url = f"/matches/{self.match_id}/rallies/{self.rally_id}/resolution"
            headers["If-Match"] = f'"{version}"'
            return self.api.request("ivy", "POST", res_url, content=raw, headers=headers)
        ids = {"match_id": self.match_id}
        if name == "correct":
            ids["rally_id"] = self.rally_id
        return self.api.run(sb.command(client, name, version=version, raw=raw, **ids))


@pytest.fixture
def target(limits_out_of_the_way: None, api: ApiDriver, committed_db: Any) -> Target:
    return Target(api, committed_db)


@pytest.fixture
def limits_out_of_the_way(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rate limits must not answer before the parser (each example is one request)."""
    for name in (
        "AUTH_LINK_LIMIT_PER_IP",
        "AUTH_LINK_LIMIT_PER_EMAIL",
        "AUTH_EXCHANGE_LIMIT_PER_IP",
    ):
        monkeypatch.setenv(name, "100000")


def _check_refused(target: Target, route: str, body: Any) -> None:
    before = sb.row_counts(target.engine)
    response = target.send(route, body)
    assert 400 <= response.status_code < 500, (
        f"{route}: {response.status_code} {response.text[:300]} for {json.dumps(body)[:200]}"
    )
    assert sb.row_counts(target.engine) == before, f"{route}: a row was written"


# ------------------------------------------------------------------ positive controls (rule 8)
def test_it_02_10_positive_controls_each_route_accepts_its_valid_body(target: Target) -> None:
    assert target.send("links", {"email": "ivy@example.com"}).status_code == 202
    assert target.send("dev_sign_in", {"username": "ivy"}).status_code == 204
    assert target.send("matches", sb.doubles_body("Fuzz control")).status_code == 201
    assert target.send("tag", VALID_TAG).status_code == 201
    assert target.send("correct", {"field": "ending", "value": "winner"}).status_code == 200
    assert target.send(
        "start_game", {"first_serving_side": "B", "ends_switched": False}
    ).status_code in (201, 409, 422)


# ------------------------------------------------------------------ strings with bad characters
@pytest.mark.parametrize("field", sorted(FIELDS))
def test_it_02_10_control_and_surrogate_characters_are_a_4xx_and_write_nothing(
    target: Target, field: str
) -> None:
    route, build, valid = FIELDS[field]
    base = valid if isinstance(valid, str) else ""

    @SETTINGS
    @given(value=bad_text(base))
    def check(value: str) -> None:
        _check_refused(target, route, build(value))

    check()


@pytest.mark.parametrize("route", KEY_ROUTES)
def test_it_02_10_bad_characters_in_an_object_key_are_a_4xx_and_write_nothing(
    target: Target, route: str
) -> None:
    valid = {
        "links": {"email": "ivy@example.com"},
        "exchange": {"token": "x" * 43},
        "dev_sign_in": {"username": "ivy"},
        "matches": sb.doubles_body("Fuzz key"),
        "start_game": {"first_serving_side": "A", "ends_switched": False},
        "tag": VALID_TAG,
        "correct": {"field": "ending", "value": "winner"},
    }[route]

    @SETTINGS
    @given(key=bad_text())
    def check(key: str) -> None:
        _check_refused(target, route, {**valid, key: "x"})

    check()


@pytest.mark.parametrize(
    "value",
    ["\x00", "\ud800", "\udfff", "\u2028", "a\x00b", "ivy\x00@example.com"],  # noqa: PT014 (ruff reads both lone surrogates as one value)
    ids=["nul", "high-surrogate", "low-surrogate", "line-separator", "inner-nul", "email-nul"],
)
@pytest.mark.parametrize("field", sorted(FIELDS))
def test_it_02_10_named_characters_in_every_field(target: Target, field: str, value: str) -> None:
    """The examples the Gherkin names (sprint-02 §14.3.1), always run, not left to chance."""
    route, build, _ = FIELDS[field]
    _check_refused(target, route, build(value))


# ------------------------------------------------------------------ any JSON value (rule 9)
@pytest.mark.parametrize("field", sorted(FIELDS))
def test_it_02_10_any_json_value_in_a_field_is_never_a_5xx(target: Target, field: str) -> None:
    route, build, _ = FIELDS[field]

    @SETTINGS
    @given(value=ANY_JSON)
    def check(value: Any) -> None:
        response = target.send(route, build(value))
        assert response.status_code < 500, (
            f"{field}: {response.status_code} {response.text[:300]} for {json.dumps(value)[:200]}"
        )

    check()
