"""Steps for tests/features/walking_skeleton.feature, API level (ST-008, ST-009, ST-010).

The UI-level version of the same journey is web/e2e/walking-skeleton.spec.ts (E2E-00-01).
Runs on the committed database because the worker runs the probe on its own connection.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import contract, tus
from tests.support.api import ApiDriver
from tests.support.format import facts_display, status_label
from tests.support.paths import SYNTHETIC_CLIP

pytestmark = pytest.mark.slow

scenarios("walking_skeleton.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("Ivy is signed in")
def ivy_signed_in(api: ApiDriver) -> None:
    api.as_user("ivy")


def _create_match(api: ApiDriver, title: str) -> str:
    response = api.request(
        "ivy", "POST", contract.MATCHES, json={"title": title, "format": "doubles"}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


@given(parsers.parse('Ivy has created a match called "{title}"'))
def ivy_created_match(api: ApiDriver, ctx: dict[str, Any], title: str) -> None:
    ctx["match_id"] = _create_match(api, title)


@given(parsers.parse('Ivy\'s upload to match "{title}" is 50% done'))
def half_uploaded(api: ApiDriver, ctx: dict[str, Any], title: str) -> None:
    ctx["match_id"] = _create_match(api, title)
    data = SYNTHETIC_CLIP.read_bytes()
    client = api.as_user("ivy")
    upload = api.run(tus.start(client, ctx["match_id"], len(data)))
    half = len(data) // 2
    response = api.run(tus.patch(client, upload, 0, data[:half]))
    assert response.status_code == 204, response.text
    contract.WORKER_RUN_UNTIL_IDLE.load()()  # a worker is running; it must find nothing to probe


@when("she uploads the 60-second synthetic fixture clip to that match")
def upload_fixture(api: ApiDriver, ctx: dict[str, Any]) -> None:
    data = SYNTHETIC_CLIP.read_bytes()
    client = api.as_user("ivy")
    upload = api.run(tus.start(client, ctx["match_id"], len(data)))
    api.run(tus.send_all(client, upload, data, chunks=3))
    processed = contract.WORKER_RUN_UNTIL_IDLE.load()()
    assert processed >= 1, "no job ran after the final byte was stored"


@when("she opens the match")
def open_match(api: ApiDriver, ctx: dict[str, Any]) -> None:
    pass  # the Then steps read the match as Ivy sees it


def _match(api: ApiDriver, ctx: dict[str, Any]) -> dict[str, Any]:
    response = api.request("ivy", "GET", contract.MATCH.format(match_id=ctx["match_id"]))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


@then(parsers.parse('the match shows the status "{label}"'))
def match_status(api: ApiDriver, ctx: dict[str, Any], label: str) -> None:
    assert status_label(_match(api, ctx)["status"]) == label


@then(
    parsers.parse(
        'the match shows duration "{duration}", frame rate "{fps}" and resolution "{resolution}"'
    )
)
def match_facts(
    api: ApiDriver, ctx: dict[str, Any], duration: str, fps: str, resolution: str
) -> None:
    media = _match(api, ctx)["media"]
    assert media is not None, "no media facts on the match"
    assert facts_display(media) == (duration, fps, resolution)


@then("no media facts are shown")
def no_facts(api: ApiDriver, ctx: dict[str, Any]) -> None:
    assert _match(api, ctx)["media"] is None
