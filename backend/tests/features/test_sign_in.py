"""API-level binding of tests/features/sign_in.feature (ST-013; sprint-01 §7.1, §14.3.1).

Binds the scenarios whose outcome the API decides; the browser spec web/e2e/sprint-01/
sign-in.spec.ts binds every scenario with the on-screen copy. "Then she sees <copy>" asserts the
API code that the FE maps to that copy (tests/support/copy.py, api-sprint-01 §1.1).
Written before ST-013: RED until it lands. Needs Mailpit for the scenarios that open a link.
"""

from __future__ import annotations

import re
import time
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.support import auth
from tests.support.api import ApiDriver
from tests.support.copy import ACCEPTED_LINK_REQUEST, ERROR_COPY, error_code

pytestmark = [pytest.mark.red_until(story="ST-013"), pytest.mark.slow]

TTL_S = 2  # MAGIC_LINK_TTL_SECONDS for this module: "16 minutes old" = older than the TTL
FEATURE = "sign_in.feature"


@pytest.fixture(autouse=True)
def _short_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAGIC_LINK_TTL_SECONDS", str(TTL_S))
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", "https://app.racket.test")


@pytest.fixture
def ctx(api: ApiDriver) -> Any:
    state: dict[str, Any] = {"client": auth.new_client(api)}
    yield state
    api.run(state["client"].aclose())


@scenario(FEATURE, "A link that can no longer be used")
def test_a_link_that_can_no_longer_be_used() -> None:
    """[API]"""


@scenario(FEATURE, "Too many link requests")
def test_too_many_link_requests() -> None:
    """[API]"""


@scenario(FEATURE, "Link requested for an unknown address")
def test_link_requested_for_an_unknown_address() -> None:
    """[API] the address is made unique per run so rate-limit windows never collide."""


@given(parsers.parse("Ivy's sign-in link {condition}"))
def ivys_link(api: ApiDriver, ctx: dict[str, Any], condition: str) -> None:
    ctx["email"] = auth.unique_email()
    assert auth.request_link(api, ctx["client"], ctx["email"]).status_code == 202
    auth.deliver_mail()
    ctx["token"] = auth.link_token(api, ctx["email"])
    if condition == "was already used":
        assert auth.exchange(api, auth.new_client(api), ctx["token"]).status_code == 200
    elif condition == "is 16 minutes old":
        time.sleep(TTL_S + 0.5)
    else:
        raise AssertionError(f"unknown condition {condition!r}")


@when("she opens it")
def she_opens_it(api: ApiDriver, ctx: dict[str, Any]) -> None:
    ctx["response"] = auth.exchange(api, ctx["client"], ctx["token"])


@then(parsers.parse('she sees "{copy}"'))
def she_sees(ctx: dict[str, Any], copy: str) -> None:
    response = ctx["response"]
    assert response.status_code == 401, response.text
    assert ERROR_COPY[error_code(response)] == copy


@then("she is offered a new link")
def offered_a_new_link(api: ApiDriver, ctx: dict[str, Any]) -> None:
    assert auth.request_link(api, ctx["client"], ctx["email"]).status_code == 202


@given(parsers.parse("Ivy has requested {n:d} sign-in links in the last 10 minutes"))
def requested_n_links(api: ApiDriver, ctx: dict[str, Any], n: int) -> None:
    ctx["email"] = auth.unique_email()
    assert [auth.request_link(api, ctx["client"], ctx["email"]).status_code for _ in range(n)] == [
        202
    ] * n


@when("she requests another one")
def requests_another(api: ApiDriver, ctx: dict[str, Any]) -> None:
    ctx["response"] = auth.request_link(api, ctx["client"], ctx["email"])


@then("she is told when she can request a new link")
def told_when(ctx: dict[str, Any]) -> None:
    response = ctx["response"]
    assert response.status_code == 429
    assert re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d", response.json()["error"]["retry_at"])


@given(parsers.parse('no account exists for "{address}"'))
def no_account(ctx: dict[str, Any], address: str) -> None:
    local, domain = address.split("@")
    ctx["unknown"] = auth.unique_email(local)
    assert ctx["unknown"].endswith("@" + domain)


@when(parsers.parse('a sign-in link is requested for "{address}"'))
def link_requested_for(api: ApiDriver, ctx: dict[str, Any], address: str) -> None:
    ctx["response"] = auth.request_link(api, ctx["client"], ctx["unknown"])


@then(parsers.parse('the page says "{copy}"'))
def page_says(ctx: dict[str, Any], copy: str) -> None:
    assert ctx["response"].status_code == 202
    assert copy == ACCEPTED_LINK_REQUEST


@then("the response is the same as for an address that has an account")
def same_as_known(api: ApiDriver, ctx: dict[str, Any]) -> None:
    known = auth.unique_email()
    assert auth.request_link(api, ctx["client"], known).status_code == 202
    auth.deliver_mail()
    assert auth.exchange(api, ctx["client"], auth.link_token(api, known)).status_code == 200
    again = auth.request_link(api, ctx["client"], known)
    unknown = ctx["response"]
    skip = {"date", "x-request-id", "traceparent", "server-timing", "content-length"}
    assert (again.status_code, again.content) == (unknown.status_code, unknown.content)
    assert sorted(k for k in again.headers if k not in skip) == sorted(
        k for k in unknown.headers if k not in skip
    )
