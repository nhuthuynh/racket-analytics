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

LIMITED = (429, {"code": "rate_limited", "retry_at": "2026-10-17T01:00:00Z"})
OK = (201, {"id": "m"})


@pytest.mark.parametrize(
    ("replies", "flags_on", "named"),
    [
        ([], True, "0 accepted, want 10"),
        ([OK] * 11 + [LIMITED] * 39, True, "11 accepted, want 10"),
        ([OK] * 9 + [LIMITED, OK] + [LIMITED] * 39, True, "accepted after a refusal"),
        ([OK] * 10 + [(429, {"code": "rate_limited", "retry_at": None})] * 40, True, "retry_at"),
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


REFUSED = {"code": "storage_quota_exceeded", "quota": {"used_bytes": 10, "limit_bytes": 10}}


@pytest.mark.parametrize(
    ("status", "body", "location", "stored", "flags_on", "named"),
    [
        (201, {}, "/u/1", (0, 0), True, "status 201"),
        (429, {"code": "upload_quota_exceeded"}, None, (0, 0), True, "code upload_quota_exceeded"),
        (429, {"code": "storage_quota_exceeded"}, None, (0, 0), True, "quota usage and limit"),
        (429, REFUSED, None, (0, 7), True, "stored bytes changed: 0 -> 7"),
        (429, REFUSED, None, (None, 0), True, "stored bytes unreadable"),
        (429, REFUSED, None, (0, 0), False, "refused by the quota with the flag off"),
    ],
)
def test_quota_problems_name_every_departure(status, body, location, stored, flags_on, named):
    found = lp.quota_problems(status, body, location, stored, flags_on=flags_on)
    assert any(named in p for p in found), found


def test_quota_refusal_before_bytes_passes() -> None:
    assert lp.quota_problems(429, REFUSED, None, (5, 5), flags_on=True) == []
    assert lp.quota_problems(201, {}, "/u/1", (None, None), flags_on=False) == []


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
