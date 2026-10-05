"""IT-01-04 (ST-014; FR-011; NFR-067; T-ML-11): every authenticated JSON response says
``Cache-Control: no-store``, and sign-out ends the session server-side and tells the browser to
clear its HTTP cache (``Clear-Site-Data: "cache"``, api-sprint-01 §2.3).

Positive control (testing-strategy rule 8): the same session works before sign-out.
"""

from __future__ import annotations

import pytest

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.flows import create_match

pytestmark = pytest.mark.red_until(story="ST-014")


def test_it_01_04_authenticated_json_is_never_cached(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-01-04"))
    urls = [
        contract.ME,
        contract.MATCHES,
        contract.MATCH.format(match_id=match_id),
        contract.UPLOAD_POLICY,
    ]
    for url in urls:
        response = api.request("ivy", "GET", url)
        assert response.status_code == 200, (url, response.status_code)
        assert response.headers["content-type"].startswith("application/json"), url
        assert "no-store" in response.headers.get("cache-control", ""), url


def test_sign_out_ends_the_session_and_clears_the_browser_cache(api: ApiDriver) -> None:
    assert api.request("ivy", "GET", contract.ME).status_code == 200  # positive control

    response = api.request("ivy", "POST", contract.AUTH_SIGN_OUT)

    assert response.status_code == 204
    assert response.headers.get("clear-site-data") == '"cache"'
    assert api.request("ivy", "GET", contract.ME).status_code == 401
    assert api.request("ivy", "POST", contract.AUTH_SIGN_OUT).status_code == 204  # idempotent
