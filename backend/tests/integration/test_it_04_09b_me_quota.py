"""IT-04-09b ``GET /me/quota`` (QA-VERIFY04R3-04; FR-160; api-sprint-04 §1 rule 2, §7, §8).
Flag off: 404 for everyone, before the session check. Flag on: 401 without a session, else 200
with the caller's own numbers in the documented shape, counted as the limits count them."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from tests.support import contract, tus
from tests.support.api import ApiDriver
from tests.support.flows import create_match

QUOTA = "/me/quota"  # api-sprint-04 §7
LENGTH = 60_000
LIMIT = 100_000


@pytest.fixture
def env(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """``FEATURE_QUOTAS`` on with a 100000-byte quota unless a test's ``env`` says otherwise."""
    values = {"FEATURE_QUOTAS": "true", "STORAGE_QUOTA_BYTES": LIMIT}
    for name, value in {**values, **getattr(request, "param", {})}.items():
        monkeypatch.setenv(name, str(value))


@pytest.mark.parametrize("env", [{"FEATURE_QUOTAS": "false"}], indirect=True)
@pytest.mark.parametrize("who", ["anonymous", "ivy"])
def test_it_04_09b_flag_off_the_route_does_not_exist_for_anyone(
    env: None, api: ApiDriver, committed_db: Any, who: str
) -> None:
    response = api.request(who, "GET", QUOTA)
    assert response.status_code == 404, response.text[:300]
    assert response.json()["error"]["code"] == "not_found"
    assert "quota" not in response.json()["error"]


def test_it_04_09b_flag_on_without_a_session_is_401(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    response = api.request("anonymous", "GET", QUOTA)
    assert response.status_code == 401, response.text[:300]


def test_it_04_09b_a_new_account_has_used_nothing(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    response = api.request("ivy", "GET", QUOTA)
    assert response.status_code == 200, response.text[:300]
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {
        "storage": {"used_bytes": 0, "limit_bytes": LIMIT},
        "match_creations": {"limit": 10, "window_s": 3600, "used": 0, "next_slot_at": None},
    }


def test_it_04_09b_usage_is_the_callers_own_and_agrees_with_the_refusal(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    ivy = api.as_user("ivy")
    api.run(tus.start(ivy, api.run(create_match(ivy, "Open")), LENGTH))
    for i in range(2):
        api.run(create_match(ivy, f"More {i}"))
    mine = api.request("ivy", "GET", QUOTA).json()
    assert mine["storage"] == {"used_bytes": LENGTH, "limit_bytes": LIMIT}
    assert mine["match_creations"]["used"] == 3
    assert mine["match_creations"]["next_slot_at"] is None
    over = api.run(tus.create(ivy, api.run(create_match(ivy, "Over")), LIMIT - LENGTH + 1))
    assert over.json()["error"]["quota"]["used_bytes"] == mine["storage"]["used_bytes"]
    carlos = api.request("carlos", "GET", QUOTA).json()
    assert carlos["storage"]["used_bytes"] == 0
    assert carlos["match_creations"]["used"] == 0


def test_it_04_09b_at_the_limit_next_slot_at_is_the_refusals_retry_at(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    ivy = api.as_user("ivy")
    for i in range(10):
        api.run(create_match(ivy, f"Hour {i}"))
    usage = api.request("ivy", "GET", QUOTA).json()["match_creations"]
    refused = api.request("ivy", "POST", contract.MATCHES, json={"title": "11", "format": "doubles"})
    assert refused.status_code == 429
    assert (usage["used"], usage["limit"]) == (10, 10)
    assert usage["next_slot_at"] == refused.json()["error"]["retry_at"]
    next_slot = datetime.fromisoformat(usage["next_slot_at"].replace("Z", "+00:00"))
    assert datetime.now(UTC) < next_slot <= datetime.now(UTC) + timedelta(hours=1)
    assert usage["next_slot_at"].endswith("Z")


def test_it_04_09b_a_stored_video_counts_until_its_match_is_deleted(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Stored"))
    upload = api.run(tus.start(ivy, match_id, LENGTH))
    api.run(tus.send_all(ivy, upload, tus.video_bytes(LENGTH)))
    assert api.request("ivy", "GET", QUOTA).json()["storage"]["used_bytes"] == LENGTH
    deleted = api.request("ivy", "DELETE", f"{contract.MATCHES}/{match_id}")
    assert deleted.status_code in (202, 204), deleted.text[:300]
    assert api.request("ivy", "GET", QUOTA).json()["storage"]["used_bytes"] == 0
