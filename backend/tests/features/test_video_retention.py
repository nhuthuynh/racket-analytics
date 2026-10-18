"""Steps for tests/features/video_retention.feature (ST-069; FR-008; api-sprint-04 §5).
The app is built with ``FEATURE_RETENTION_SETTING`` from the scenario on the committed
database; the purge runs through its entry point with ``--now-offset-days``."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import retention as rt
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

scenarios("video_retention.feature")

USERS = {"Ivy": "ivy", "Carlos": "carlos"}


@pytest.fixture
def drivers() -> Iterator[list[ApiDriver]]:
    built: list[ApiDriver] = []
    yield built
    for driver in built:
        driver.close()


@pytest.fixture
def matches() -> dict[str, str]:
    return {}


@given(parsers.re(r"the retention setting is (?P<state>on|off)"), target_fixture="api")
def retention_flag(
    state: str, monkeypatch: pytest.MonkeyPatch, committed_db: Any, drivers: list[ApiDriver]
) -> ApiDriver:
    drivers.append(rt.build_api(monkeypatch, on=state == "on"))
    return drivers[-1]


@given(parsers.re(r"(?P<who>Ivy|Carlos) has a tagged match whose video was analysed"))
def analysed(api: ApiDriver, who: str, matches: dict[str, str]) -> None:
    matches[who] = rt.analysed_match(api, USERS[who], f"ST-069 {who}")


@given(parsers.re(r"(?P<who>Ivy|Carlos) keeps review video for (?P<days>\d+) days"))
def keeps(api: ApiDriver, who: str, days: str) -> None:
    response = rt.put_days(api, USERS[who], int(days))
    assert response.status_code == 200, response.text


@when(parsers.re(r"the purge runs (?P<days>\d+) days later"))
def purge_later(days: str) -> None:
    assert rt.run_purge("--now-offset-days", days) == 0


@then(parsers.re(r"(?P<who>Ivy|Carlos)'s review video is still stored"))
def still_stored(committed_db: Any, who: str, matches: dict[str, str]) -> None:
    assert rt.stored(committed_db, matches[who])
    assert rt.media_rows(committed_db, matches[who]) == 1


@then(parsers.re(r"(?P<who>Ivy|Carlos)'s review video is gone"))
def gone(api: ApiDriver, committed_db: Any, who: str, matches: dict[str, str]) -> None:
    assert not rt.stored(committed_db, matches[who])
    assert rt.media_rows(committed_db, matches[who]) == 0
    assert rt.video_link(api, USERS[who], matches[who]).status_code == 409


@then("the match shows no deletion date")
def no_date(api: ApiDriver, matches: dict[str, str]) -> None:
    assert rt.FIELD not in rt.match_body(api, "ivy", matches["Ivy"])


@then("the retention setting is not found")
def not_found(api: ApiDriver) -> None:
    assert api.request("ivy", "GET", rt.RETENTION).status_code == 404
    assert rt.put_days(api, "ivy", 30).status_code == 404


@then(parsers.re(r"the match shows the deletion date (?P<days>\d+) days after the analysis"))
def shows_date(api: ApiDriver, committed_db: Any, days: str, matches: dict[str, str]) -> None:
    shown = rt.match_body(api, "ivy", matches["Ivy"])[rt.FIELD]
    expected = rt.analysed_at(committed_db, matches["Ivy"]) + timedelta(days=int(days))
    assert abs(rt.parse_utc(shown) - expected) < timedelta(seconds=1), shown


@then("the stats and the score sheet of the match are still there")
def stats_stay(api: ApiDriver, matches: dict[str, str]) -> None:
    assert st.stats(api, "ivy", matches["Ivy"]).status_code == 200
    assert sb.sheet_body(api, "ivy", matches["Ivy"])["rows"]
