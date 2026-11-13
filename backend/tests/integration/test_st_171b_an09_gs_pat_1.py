"""ST-171b (FR-171.R2, R3; ADR 0044): AN-09 on the gold fixture GS-PAT-1 equals the coach's hand
count, rally by rally, across the Dataset -> Analytics boundary.

The fixture file ``docs/domain/hand-counts/GS-PAT-1-v1.json`` is read from disk; each match's
labels must pass the publisher's validator (``racket.dataset.labels``, FR-150) before Analytics
reads them through its ACL (``racket.analytics.patterns.full_tag``). The catalogue's worked
example W-09-a and its definition version and interval method are read from
``docs/domain/pattern-catalogue.md``. Written red first (no extractor).
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from racket.analytics.patterns.full_tag import full_tag_measures, read_rallies
from racket.analytics.patterns.third_shot import AN09, AN09_MIN_N, third_shots
from racket.analytics.uncertainty import wilson
from racket.dataset.labels import validate_labels
from racket.sports.references.loader import parse_catalogue
from tests.support.paths import REPO

pytestmark = [pytest.mark.analytics]

FIXTURE = REPO / "docs" / "domain" / "hand-counts" / "GS-PAT-1-v1.json"
CATALOGUE = REPO / "docs" / "domain" / "pattern-catalogue.md"
MATCHES = ("gp1-doubles", "gp2-singles")


def _fixture() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def _ids(buckets: dict[str, Any]) -> dict[str, list[str]]:
    return {key: sorted(ids) for key, ids in buckets.items() if ids}


@pytest.mark.parametrize("match", MATCHES)
@pytest.mark.parametrize("side", ["A", "B"])
def test_an09_equals_the_coach_hand_count_rally_by_rally(match: str, side: str) -> None:
    entry = _fixture()["matches"][match]
    labels = entry["labels"]
    assert validate_labels(labels) == ()
    hand = entry["counts"]["AN-09"][side]
    tally = third_shots(read_rallies(labels), side)
    assert _ids(dict(tally.mix)) == _ids(hand["mix"])
    assert _ids(dict(tally.excluded)) == _ids(hand["excluded"])
    m = full_tag_measures(labels)[AN09][side]
    k, n = len(hand["mix"].get("drop", [])), sum(len(v) for v in hand["mix"].values())
    assert (m.n, m.n_excluded) == (n, sum(len(v) for v in hand["excluded"].values()))
    assert (m.value, m.interval) == ((k / n if n else None), wilson(k, n))
    assert (m.low_sample, m.agreement) == (n < AN09_MIN_N, "not_measured")


def test_worked_example_w_09_a_gives_the_catalogue_counts() -> None:
    text = CATALOGUE.read_text(encoding="utf-8")
    block = re.search(r"<!-- example: W-09-a -->\s*```json\n(.*?)```\s*<!-- expect: (.*?) -->",
                      text, re.S)  # fmt: skip
    assert block is not None
    labels, expect = json.loads(block[1]), json.loads(block[2])
    read = read_rallies(labels)
    a, b = third_shots(read, "A"), third_shots(read, "B")
    assert (a.k, a.n) == (expect["AN-09@A"]["k"], expect["AN-09@A"]["n"])
    assert {r: len(ids) for r, ids in a.excluded.items()} == expect["AN-09@A"]["excluded"]
    assert {r: len(ids) for r, ids in a.unassigned.items()} == expect["AN-09@A"]["unassigned"]
    assert (b.k, b.n) == (expect["AN-09@B"]["k"], expect["AN-09@B"]["n"])
    assert {t: len(ids) for t, ids in b.mix.items()} == expect["AN-09@B"]["mix"]


def test_definition_version_interval_method_and_min_n_equal_the_catalogue() -> None:
    text = CATALOGUE.read_text(encoding="utf-8")
    pattern = parse_catalogue(text)[AN09]
    labels = _fixture()["matches"]["gp1-doubles"]["labels"]
    m = full_tag_measures(labels)[AN09]["A"]
    assert (m.definition_version, m.interval_method) == (
        pattern.definition_version, pattern.interval_method,
    )  # fmt: skip
    row = re.search(r"^\| AN-09 \|(?:[^|]*\|){3} (\d+) \|", text, re.M)
    assert row is not None
    assert int(row[1]) == AN09_MIN_N
