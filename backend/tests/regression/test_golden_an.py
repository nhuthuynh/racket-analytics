"""Golden matches GS-AN-1 v1 (ST-049; QD-GD-03; NFR-004 exact, FR-151 / NFR-078 frozen set).

Three tag scripts under the provisional preset (``golden_matches/*.script.json``):

* ``gm1-two-games``: A wins game 1, B wins game 2 (59 rallies, every ending incl. replays);
* ``gm2-three-games``: A, B, A (59 rallies, every ending incl. replays);
* ``gm3-corrections-needs-decision``: one game, two corrections (an ending, then a winner that
  ends the game earlier), so its last 4 rallies are kept as "needs your decision" and excluded
  (metric-dictionary rule 0.1).

Each script is driven through the real scorebook commands (start game, tag, correct) with fixed
ids and clock, projected (ST-026), and fed to the product's ``racket.analytics.starter_stats``
(ST-044). The result must equal the frozen expected values exactly, for every metric, side
and match; a difference names all three (NFR-004). The expected values are also re-derived
from the independent reference ``scripts/measure/statslib.py``, so a wrong frozen file cannot
pass, and the set is checked by ``racket-manifest-check`` (no change without a version bump).

The expected values are the coach's hand counts only once COACH-1 has counted the scripts
(QD-AN-03) into ``docs/domain/hand-counts/GS-AN-1-v1.json``, a file the coach owns; until it
exists and equals the frozen values, the last test stays red (``red_until COACH-1``).
AN-01, AN-02, AN-03, AN-05 and AN-06 read the provisional score sequence, so their rows
carry ``needs_verification`` and are reported on their own line (QD-QG-P5, scorecard G03-08).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from racket.analytics.starter_stats import starter_stats
from racket.dataset import cli as manifest_cli
from tests.regression.test_golden_replay import Fixture
from tests.support.scorebook import _load

statslib = _load("statslib")

pytestmark = [pytest.mark.golden_an, pytest.mark.analytics]

SET_DIR = Path(__file__).with_name("golden_matches")
REPO = Path(__file__).resolve().parents[3]
HAND_COUNTS = REPO / "docs" / "domain" / "hand-counts" / "GS-AN-1-v1.json"
MATCHES = (
    "gm1-two-games",
    "gm2-three-games",
    "gm3-corrections-needs-decision",
)
METRICS = statslib.METRICS
RULE_DEPENDENT = {"AN-01", "AN-02", "AN-03", "AN-05", "AN-06"}  # read the provisional sequence
SIDES = ("A", "B")


def script(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((SET_DIR / f"{name}.script.json").read_text())
    return data


def expected(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((SET_DIR / "expected" / f"{name}.json").read_text())
    return data


class GoldenFixture(Fixture):
    def correct(self, number: int, field: str, value: Any) -> GoldenFixture:
        self.book = self.book.correct(
            self.rally_ids[number - 1], field, value,
            expected_version=self.book.version, ctx=self.ctx,
        )  # fmt: skip
        return self


def product_stats(s: dict[str, Any]) -> dict[str, Any]:
    fixture = GoldenFixture()
    for game in s["games"]:
        fixture.start(game["first_serving_side"]).tag(game["tags"])
    for c in s["corrections"]:
        fixture.correct(c["rally"], c["field"], c["value"])
    sheet = fixture.sheet()
    assert {g["rules_version"] for g in sheet["games"]} == {s["rules_version"]}
    return dict(starter_stats(sheet))


def reference_stats(s: dict[str, Any]) -> dict[str, Any]:
    games = copy.deepcopy(s["games"])
    flat = [t for g in games for t in g["tags"]]
    for c in s["corrections"]:
        flat[c["rally"] - 1][c["field"]] = c["value"]
    return dict(statslib.starter_stats(games))


def differences(match: str, metric: str, want: dict[str, Any], got: dict[str, Any]) -> list[str]:
    out = []
    for side in SIDES:
        for key, value in want[side].items():
            actual = got.get(side, {}).get(key)
            if actual != value:
                where = f"GS-AN-1 {match} {metric} side {side} {key}"
                out.append(f"{where}: expected {value!r}, got {actual!r}")
    return out


def _cases() -> list[Any]:
    cases = []
    for match in MATCHES:
        for metric in METRICS:
            marks = [pytest.mark.needs_verification] if metric in RULE_DEPENDENT else []
            cases.append(pytest.param(match, metric, id=f"GS-AN-1-{match}-{metric}", marks=marks))
    return cases


_PRODUCT: dict[str, dict[str, Any]] = {}


def _product(match: str) -> dict[str, Any]:
    if match not in _PRODUCT:
        _PRODUCT[match] = product_stats(script(match))
    return _PRODUCT[match]


# ---------------------------------------------------------------- negative first: the check bites
def test_golden_an_a_changed_rally_is_reported_naming_match_metric_and_side() -> None:
    """Mutant check: gm1's first unforced error re-tagged as a forced error (same score, so
    the games still end where they did) no longer matches."""
    s = script("gm1-two-games")
    tag = next(t for t in s["games"][0]["tags"] if t["ending"] == "unforced_error")
    tag["ending"] = "forced_error"
    got = product_stats(s)
    want = expected("gm1-two-games")["metrics"]
    found = [d for m in METRICS for d in differences("gm1-two-games", m, want[m], got[m])]
    assert found, "a switched winner went unnoticed"
    assert found[0].startswith("GS-AN-1 gm1-two-games AN-")
    assert " side " in found[0]


def test_golden_an_set_has_exactly_the_three_v1_matches() -> None:
    scripts = sorted(p.name.removesuffix(".script.json") for p in SET_DIR.glob("*.script.json"))
    expect = sorted(p.stem for p in (SET_DIR / "expected").glob("*.json"))
    assert scripts == sorted(MATCHES)
    assert expect == sorted(MATCHES)
    games = {m: len(script(m)["games"]) for m in MATCHES}
    assert games == {
        "gm1-two-games": 2,
        "gm2-three-games": 3,
        "gm3-corrections-needs-decision": 1,
    }
    assert script("gm3-corrections-needs-decision")["corrections"], "gm3 needs its corrections"


def test_golden_an_gm3_keeps_rallies_that_need_a_decision() -> None:
    s = script("gm3-corrections-needs-decision")
    fixture = GoldenFixture()
    fixture.start("A").tag(s["games"][0]["tags"])
    for c in s["corrections"]:
        fixture.correct(c["rally"], c["field"], c["value"])
    markers = [r["marker"] for r in fixture.sheet()["rows"]]
    assert markers.count("needs_decision") == 4
    assert markers[-4:] == ["needs_decision"] * 4


# ---------------------------------------------------------------- the gate (NFR-004: 100% exact)
@pytest.mark.parametrize(("match", "metric"), _cases())
def test_golden_an_product_equals_the_frozen_values(match: str, metric: str) -> None:
    want = expected(match)["metrics"][metric]
    got = _product(match)[metric]
    found = differences(match, metric, want, got)
    assert not found, "\n".join(found)


@pytest.mark.parametrize("match", MATCHES)
def test_golden_an_frozen_values_equal_the_independent_reference(match: str) -> None:
    want = expected(match)["metrics"]
    ref = reference_stats(script(match))
    found = [
        f"{match} {m} {side} {k}: frozen {want[m][side][k]!r}, reference {ref[m][side][k]!r}"
        for m in METRICS
        for side in SIDES
        for k in want[m][side]
        if want[m][side][k] != ref[m][side][k]
    ]
    assert not found, "\n".join(found)


def test_golden_an_manifest_is_intact() -> None:
    """FR-151 / NFR-078: every file listed with its sha256; no unlisted or changed file."""
    assert manifest_cli.main([str(SET_DIR)]) == 0
    manifest = json.loads((SET_DIR / "manifest.json").read_text())
    assert manifest["id"] == "GS-AN-1"
    assert manifest["version"] == 1
    assert manifest["rules_version"] == "PROVISIONAL-UNVERIFIED"
    assert manifest["metric_dict_version"] == "0.1"
    assert manifest["labellers"], "the labeller role is recorded (FR-151)"


@pytest.mark.red_until(story="COACH-1")
@pytest.mark.parametrize("match", MATCHES)
def test_golden_an_frozen_values_are_the_coachs_hand_count(match: str) -> None:
    """QD-AN-03: the coach hand-counts each script on paper and records the count, in the
    frozen file's shape, in ``docs/domain/hand-counts/GS-AN-1-v1.json`` (``{"by", "date",
    "matches": {match: {metric: {side: {field: value}}}}}``; ``rallies`` optional). Every
    counted field must equal the frozen value; a difference is a finding for QA and the coach,
    never an edit to make this pass."""
    assert HAND_COUNTS.exists(), f"no hand count yet: {HAND_COUNTS.relative_to(REPO)} (COACH-1)"
    record = json.loads(HAND_COUNTS.read_text())
    assert record.get("by") == "pickleball-domain-coach"
    assert record.get("date")
    counted = record["matches"][match]
    want = expected(match)["metrics"]
    missing = [
        f"{m} {side} {k}"
        for m in METRICS
        for side in SIDES
        for k in statslib.COMPARED[m]
        if k not in counted.get(m, {}).get(side, {})
    ]
    assert not missing, f"{match}: not hand-counted: {missing}"
    found = [d for m in METRICS for d in differences(match, m, counted[m], want[m])]
    assert not found, "hand count (expected) vs frozen (got):\n" + "\n".join(found)
