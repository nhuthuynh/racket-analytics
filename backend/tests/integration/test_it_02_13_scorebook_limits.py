"""IT-02-13 (SEC-S2-R1-01; ASVS 5.0 2.4.1; AQS/SEC-10; testing-strategy L11): scorebook commands
are limited, and the history is paginated.

* per-match caps (``SCOREBOOK_MAX_RALLIES``, ``SCOREBOOK_MAX_CHANGES``): the command past the cap
  is 422 ``scorebook_full`` and writes nothing;
* per-account command rate (``SCOREBOOK_COMMAND_LIMIT_PER_MINUTE``): 12 parallel commands with a
  limit of 5 give exactly 5 x 201 and 7 x 429 ``rate_limited`` with ``Retry-After``
  (concurrency case, rule L11); a refused command writes nothing, its rate hit included;
* ``GET …/corrections?limit=&cursor=``: pages oldest first with ``next_cursor``; bad paging
  values are 422 with a field code.

Small caps through the environment keep the test fast; the defaults are in the decision-log.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

import httpx
import pytest

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

TAG = {"winning_side": None, "ending": "replay", "responsible_player": None, "fault_kind": None}


def _tag(n: int) -> dict[str, Any]:
    return {**TAG, "start_ms": n * 1_000, "end_ms": n * 1_000 + 900}


def _ready(api: ApiDriver, title: str) -> tuple[httpx.AsyncClient, str]:
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, title))
    api.run(sb.receive_video(ivy, match_id))
    api.run(sb.start_game(ivy, match_id))
    return ivy, match_id


def _error(response: httpx.Response) -> tuple[int, str, list[tuple[Any, Any]]]:
    error = response.json()["error"]
    fields = [(f["field"], f["code"]) for f in error.get("fields", [])]
    return response.status_code, error["code"], fields


@pytest.fixture
def small_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCOREBOOK_MAX_RALLIES", "3")
    monkeypatch.setenv("SCOREBOOK_MAX_CHANGES", "4")


def test_it_02_13_a_tag_past_the_rally_cap_is_refused_and_writes_nothing(
    small_caps: None, api: ApiDriver, committed_db: Any
) -> None:
    ivy, match_id = _ready(api, "IT-02-13 rallies")
    api.run(sb.tag_all(ivy, match_id, [_tag(n) for n in range(3)]))
    version = api.run(sb.version_of(ivy, match_id))
    before = sb.row_counts(committed_db)
    refused = api.run(sb.command(ivy, "tag", version=version, body=_tag(9), match_id=match_id))
    assert _error(refused) == (422, "scorebook_full", [(None, "too_many_rallies")])
    assert sb.row_counts(committed_db) == before
    assert api.run(sb.version_of(ivy, match_id)) == version


def test_it_02_13_a_change_past_the_change_cap_is_refused_and_writes_nothing(
    small_caps: None, api: ApiDriver, committed_db: Any
) -> None:
    ivy, match_id = _ready(api, "IT-02-13 changes")  # audit row 1: the game start
    tagged = api.run(sb.tag_all(ivy, match_id, [_tag(0)]))
    rally_id = tagged[0].json()[sb.tagcontract.RALLY_ID_KEY]

    def correct(start_ms: int) -> httpx.Response:
        version = api.run(sb.version_of(ivy, match_id))
        body = {"field": "start_ms", "value": start_ms}
        return api.run(
            sb.command(ivy, "correct", version=version, body=body,
                       match_id=match_id, rally_id=rally_id)
        )  # fmt: skip

    for start_ms in (10, 20, 30):  # audit rows 2-4
        assert correct(start_ms).status_code == 200
    before = sb.row_counts(committed_db)
    assert _error(correct(40)) == (422, "scorebook_full", [(None, "too_many_changes")])
    version = api.run(sb.version_of(ivy, match_id))
    undo = api.run(sb.command(ivy, "undo", version=version, match_id=match_id))
    assert _error(undo) == (422, "scorebook_full", [(None, "too_many_changes")])
    assert sb.row_counts(committed_db) == before


@pytest.fixture
def five_per_minute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCOREBOOK_COMMAND_LIMIT_PER_MINUTE", "5")
    monkeypatch.setenv("UPLOAD_CREATE_LIMIT_PER_HOUR", "1000")  # 12 uploads to set up
    monkeypatch.setenv("UPLOAD_MAX_OPEN_SESSIONS", "1000")


@pytest.mark.parametrize("attempt", range(3))
def test_it_02_13_parallel_commands_never_pass_the_per_account_rate(
    five_per_minute: None, api: ApiDriver, committed_db: Any, attempt: int
) -> None:
    """12 game starts on 12 matches at once (one match would serialise them on its version):
    exactly 5 are saved. A refused command writes nothing, its rate hit included."""
    ivy = api.as_user("ivy")
    match_ids = [api.run(sb.create_doubles(ivy, f"IT-02-13 rate {attempt}.{i}")) for i in range(12)]
    for match_id in match_ids:
        api.run(sb.receive_video(ivy, match_id))
    body = {"first_serving_side": "A", "ends_switched": False}

    async def burst() -> list[httpx.Response]:
        return list(
            await asyncio.gather(
                *(sb.command(ivy, "start_game", version=0, body=body, match_id=m)
                  for m in match_ids)
            )
        )  # fmt: skip

    responses = api.run(burst())
    seen = Counter(
        (r.status_code, None if r.status_code < 400 else _error(r)[1]) for r in responses
    )
    assert seen == {(201, None): 5, (429, "rate_limited"): 7}, seen
    limited = next(r for r in responses if r.status_code == 429)
    assert int(limited.headers["Retry-After"]) >= 1
    counts = sb.row_counts(committed_db)
    hits = counts["rate_limit_events"] - 12  # the 12 upload creations count on their own key
    assert (counts["match_games"], hits) == (5, 5)


def test_it_02_13_the_history_is_paginated_oldest_first(api: ApiDriver) -> None:
    ivy, match_id = _ready(api, "IT-02-13 history")
    api.run(sb.tag_all(ivy, match_id, [_tag(n) for n in range(4)]))
    for _ in range(4):  # 4 undos: 4 withdrawals; with the game start, 5 history items
        version = api.run(sb.version_of(ivy, match_id))
        assert (
            api.run(sb.command(ivy, "undo", version=version, match_id=match_id)).status_code == 200
        )
    url = f"/matches/{match_id}/corrections"
    everything = api.run(ivy.get(url)).json()
    assert len(everything["items"]) == 5
    assert everything["next_cursor"] is None

    pages: list[dict[str, Any]] = []
    page = api.run(ivy.get(url, params={"limit": 2})).json()
    pages.append(page)
    while page["next_cursor"] is not None:
        page = api.run(ivy.get(url, params={"limit": 2, "cursor": page["next_cursor"]})).json()
        pages.append(page)
    assert [len(p["items"]) for p in pages] == [2, 2, 1]
    assert [i["id"] for p in pages for i in p["items"]] == [i["id"] for i in everything["items"]]


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"limit": 0}, "limit"),
        ({"limit": 201}, "limit"),
        ({"limit": "x"}, "limit"),
        ({"cursor": "abc"}, "cursor"),
        ({"cursor": "-1"}, "cursor"),
    ],
)
def test_it_02_13_bad_paging_values_are_422(
    api: ApiDriver, params: dict[str, Any], field: str
) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, "IT-02-13 paging"))
    response = api.run(ivy.get(f"/matches/{match_id}/corrections", params=params))
    assert _error(response) == (422, "validation_failed", [(field, "invalid")])
