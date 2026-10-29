"""Unit tests of the pure verdicts of scripts/measure/live_privacy.py (QA-HARNESS-4b).

Negative cases first: a short, empty or malformed observation never reads as a pass (fail
closed, ADR 0014). G04-10 (a) wants exactly 10 accepted of 50 and none after the first refusal.
"""

from __future__ import annotations

import sys

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit
sys.path.insert(0, str(SCRIPTS_DIR / "measure"))
import live_privacy as lp  # noqa: E402


def err(code: str, **extra: object) -> dict[str, object]:
    """The API's error body (api-sprint-01 §1.1; backend/src/racket/platform/errors.py)."""
    return {"error": {"code": code, "message": "m", "support_ref": "ref_0123456789abcdef", **extra}}


LIMITED = (429, err("rate_limited", retry_at="2026-10-17T01:00:00Z"))
OK = (201, {"id": "m"})


@pytest.mark.parametrize(
    ("replies", "flags_on", "named"),
    [
        ([], True, "0 accepted, want 10"),
        ([OK] * 11 + [LIMITED] * 39, True, "11 accepted, want 10"),
        ([OK] * 9 + [LIMITED, OK] + [LIMITED] * 39, True, "accepted after a refusal"),
        ([OK] * 10 + [(429, err("rate_limited", retry_at=None))] * 40, True, "retry_at"),
        ([OK] * 10 + [(500, {})] * 40, True, "status 500"),
        ([OK] * 10 + [LIMITED] * 40, False, "10 accepted, want 50"),
    ],
)
def test_burst_problems_name_every_departure(replies, flags_on, named) -> None:
    assert any(named in p for p in lp.burst_problems(replies, flags_on=flags_on))


@pytest.mark.parametrize(("replies", "flags_on"), [([OK] * 10 + [LIMITED] * 40, True),
                                                    ([OK] * 50, False)])  # fmt: skip
def test_burst_exact_limit_passes(replies, flags_on) -> None:
    assert lp.burst_problems(replies, flags_on=flags_on) == []


REFUSED = err("storage_quota_exceeded", retry_at=None,
              quota={"used_bytes": 10, "limit_bytes": 10, "requested_bytes": 1})  # fmt: skip


@pytest.mark.parametrize(
    ("status", "body", "location", "stored", "flags_on", "named"),
    [
        (201, {}, "/u/1", (0, 0), True, "status 201"),
        (429, err("upload_quota_exceeded"), None, (0, 0), True, "code upload_quota_exceeded"),
        (429, err("storage_quota_exceeded"), None, (0, 0), True, "quota usage and limit"),
        (429, REFUSED, None, (0, 7), True, "stored bytes changed: 0 -> 7"),
        (429, REFUSED, None, (None, 0), True, "stored bytes unreadable"),
        (429, REFUSED, None, (0, 0), False, "refused by the quota with the flag off"),
        (500, err("internal_error"), None, (None, None), False, "status 500"),
        (404, None, None, (None, None), False, "status 404"),
        (201, {}, None, (None, None), False, "Location None"),
    ],
)
def test_quota_problems_name_every_departure(status, body, location, stored, flags_on, named):
    found = lp.quota_problems(status, body, location, stored, flags_on=flags_on)
    assert any(named in p for p in found), found


def test_quota_refusal_before_bytes_passes() -> None:
    assert lp.quota_problems(429, REFUSED, None, (5, 5), flags_on=True) == []
    assert lp.quota_problems(201, {}, "/u/1", (None, None), flags_on=False) == []


def test_flags_off_open_session_cap_is_todays_behaviour_not_a_failure() -> None:
    # api-sprint-01 §6.3 check 5: a 4th open upload session is 429 upload_quota_exceeded
    sessions = err("upload_quota_exceeded", retry_at=None)
    assert lp.quota_problems(429, sessions, None, (None, None), flags_on=False) == []
    found = lp.quota_problems(429, err("rate_limited"), None, (None, None), flags_on=False)
    assert any("status 429" in p for p in found), found


FLAT = dict(REFUSED["error"])  # the pre-fix reading: no envelope


@pytest.mark.parametrize("body", [None, {}, {"error": None}, {"error": "rate_limited"}, FLAT])
def test_error_of_reads_only_the_error_envelope(body) -> None:
    # QA-VERIFY04R3-03: a code at the top level is not the API's body; it reads as absent
    assert lp.error_of(body) == {}


def test_error_of_returns_the_error_object() -> None:
    assert lp.error_of(REFUSED) == REFUSED["error"]


def test_refusals_outside_the_envelope_are_not_read_as_refusals() -> None:
    flat_limited = (429, {"code": "rate_limited", "retry_at": "2026-10-17T01:00:00Z"})
    assert "status 429 None" in lp.burst_problems([OK] * 10 + [flat_limited] * 40, flags_on=True)
    found = lp.quota_problems(429, FLAT, None, (0, 0), flags_on=True)
    assert "code None" in found, found
    assert "body lacks quota usage and limit" in found, found
    flat_cap = {"code": "upload_quota_exceeded"}
    found = lp.quota_problems(429, flat_cap, None, (None, None), flags_on=False)
    assert any("status 429" in p for p in found), found


@pytest.mark.parametrize(
    ("limit", "used", "max_bytes", "sizes"),
    [(0, 0, 10, []), (10, 10, 4, []), (10, 0, 4, [4, 4, 2]), (21_474_836_480, 0, 10**10,
     [10**10, 10**10, 1_474_836_480])],
)  # fmt: skip
def test_fill_sizes_reach_the_limit_exactly(limit, used, max_bytes, sizes) -> None:
    assert lp.fill_sizes(limit, used, max_bytes) == sizes


@pytest.mark.parametrize("bad", [(10, 0, 0), (-1, 0, 4)])
def test_fill_sizes_refuse_a_size_that_cannot_fill(bad) -> None:
    with pytest.raises(ValueError, match="cannot fill"):
        lp.fill_sizes(*bad)


@pytest.mark.parametrize(("text", "value"), [("", None), ("none\n", None), ("12\n", 12),
                                             ('{"size": 4096}', 4096), (" 3 rows", 3)])  # fmt: skip
def test_first_int_reads_the_first_integer_or_none(text, value) -> None:
    assert lp.first_int(text) == value


@pytest.mark.parametrize(
    ("rc", "out", "rules", "named"),
    [(1, "SUCCESS", 6, "alert test rc=1"), (0, "FAILED:", 6, "no SUCCESS"),
     (0, "SUCCESS", 5, "5 billing alert rules, want 6")],
)  # fmt: skip
def test_alert_problems_name_every_departure(rc, out, rules, named) -> None:
    assert any(named in p for p in lp.alert_problems(rc, out, rules))


def test_alert_rule_test_success_with_six_rules_passes() -> None:
    assert lp.alert_problems(0, "Unit Testing: billing.test.yml\n  SUCCESS\n", 6) == []


FAIL, PASS = {"ok": False, "problems": ["x"]}, {"ok": True, "problems": []}


@pytest.mark.parametrize(
    "out",
    [
        {"runs": []},
        {"runs": [{}]},
        {"runs": [{"age": PASS, "consent": FAIL}]},
        {"runs": [{"flags_off": PASS}, {"flags_off": FAIL}]},
        {"runs": [{"flags_off": PASS}], "quotas": {"burst": PASS, "alerts": FAIL}},
        {"runs": [{"flags_off": PASS}], "quotas": {"burst": PASS, "quota": {"problems": []}}},
    ],
)
def test_verdict_fails_when_any_step_fails_or_nothing_ran(out) -> None:
    assert lp.verdict(out) is False


def test_verdict_passes_only_when_every_step_passes() -> None:
    out = {"runs": [{"flags_off": PASS}], "quotas": {"burst": PASS, "quota": PASS, "alerts": PASS}}
    assert lp.verdict(out) is True
