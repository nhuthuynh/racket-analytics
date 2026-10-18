"""Steps for tests/features/training_consent.feature (ST-070; FR-009; api-sprint-04 §6).
The app is built with ``FEATURE_TRAINING_CONSENT`` from the scenario on the committed database;
the label set is built through its entry point, as an operator runs it."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import consent as cs
from tests.support.api import ApiDriver

scenarios("training_consent.feature")

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


@pytest.fixture
def builds() -> dict[str, Any]:
    return {}


@given(parsers.re(r"the training consent setting is (?P<state>on|off)"), target_fixture="api")
def consent_flag(
    state: str, monkeypatch: pytest.MonkeyPatch, committed_db: Any, drivers: list[ApiDriver]
) -> ApiDriver:
    drivers.append(cs.build_api(monkeypatch, on=state == "on"))
    return drivers[-1]


@given(parsers.re(r"(?P<who>Ivy|Carlos) has a tagged match$"))
def tagged(api: ApiDriver, who: str, matches: dict[str, str]) -> None:
    matches[who] = cs.tagged_match(api, USERS[who], f"ST-070 {who}")


@given(parsers.re(r"(?P<who>Ivy|Carlos) has a tagged match with a team-held consent record"))
def tagged_with_record(api: ApiDriver, who: str, matches: dict[str, str]) -> None:
    matches[who] = cs.tagged_match(api, USERS[who], f"ST-070 {who} team record")
    cs.record_team_consent(matches[who])


@given(parsers.re(r"(?P<who>Ivy|Carlos) has not opted in to training use"))
def not_opted_in(api: ApiDriver, who: str) -> None:
    got = api.request(USERS[who], "GET", cs.CONSENT)
    assert got.status_code == 200, got.text
    assert got.json()["opt_in"] is False


@given(parsers.re(r"(?P<who>Ivy|Carlos) opted in to training use"))
def opted_in(api: ApiDriver, who: str) -> None:
    response = cs.put_opt_in(api, USERS[who], True)
    assert response.status_code == 200, response.text


@given("the label set built then holds Ivy's match")
def first_build(tmp_path: Path, matches: dict[str, str], builds: dict[str, Any]) -> None:
    path = tmp_path / "label-set-v1.json"
    assert matches["Ivy"] in cs.build_to(path)
    builds["before"] = (path, path.read_bytes())


@when(parsers.re(r"(?P<who>Ivy|Carlos) revokes training use"))
def revokes(api: ApiDriver, who: str) -> None:
    response = cs.put_opt_in(api, USERS[who], False)
    assert response.status_code == 200, response.text


@when("the next label set is built")
def next_build(tmp_path: Path, builds: dict[str, Any]) -> None:
    builds["next"] = cs.build_to(tmp_path / "label-set-next.json")


@then(parsers.re(r"none of Ivy's matches (or corrections )?are in it"))
def ivy_absent(matches: dict[str, str], builds: dict[str, Any]) -> None:
    assert matches["Ivy"] not in builds["next"]


@then(parsers.re(r"(?P<who>Ivy|Carlos)'s match is in it"))
def present(who: str, matches: dict[str, str], builds: dict[str, Any]) -> None:
    assert matches[who] in builds["next"]


@then("the label set built before the revoke is unchanged")
def frozen(matches: dict[str, str], builds: dict[str, Any]) -> None:
    path, content = builds["before"]
    assert path.read_bytes() == content
    assert matches["Ivy"] in cs.built_match_ids(content.decode("utf-8"))


@then("the training consent setting is not found")
def not_found(api: ApiDriver) -> None:
    assert api.request("ivy", "GET", cs.CONSENT).status_code == 404
    assert cs.put_opt_in(api, "ivy", True).status_code == 404
