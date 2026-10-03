"""QA-R1-04: E2E-00-01's empty-state step needs a dev account that no spec ever gives a match,
so the result does not depend on spec order. The dev identity provider offers "Dana" for that.
"""

from __future__ import annotations

from tests.support import contract
from tests.support.api import ApiDriver


def test_dana_is_offered_by_the_dev_identity_provider(api: ApiDriver) -> None:
    users = api.request("anonymous", "GET", "/dev/users").json()["items"]

    assert {"username": "dana", "display_name": "Dana"} in users


def test_dana_can_sign_in_and_starts_with_no_matches(api: ApiDriver) -> None:
    listing = api.request("dana", "GET", contract.MATCHES)

    assert listing.status_code == 200
    assert listing.json()["items"] == []
