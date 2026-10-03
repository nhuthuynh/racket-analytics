"""The scenario report lists @needs-verification scenarios separately (ST-004; QD-QG-P5)."""

from __future__ import annotations

from pathlib import Path

from tests.tools.scenario_report import collect, render

FEATURE = """@M0 @story-ST-099
Feature: Scoring

  Rule: Side-out
    @needs-verification
    Scenario Outline: Receiver wins the rally
      Given a score "<before>"
      Then the score is "<after>"
      Examples:
        | before | after |
        | 0-0-2  | 0-0-2 |

    Scenario: Ivy's verified one
      Given something
      Then something else
"""

JUNIT = """<?xml version="1.0"?>
<testsuites><testsuite>
  <testcase classname="tests.features.test_scoring" name="test_ivys_verified_one"/>
  <testcase classname="t" name="test_receiver_wins_the_rally[0-0-2-0-0-2]">
    <failure message="boom"/>
  </testcase>
</testsuite></testsuites>
"""


def _write(tmp_path: Path) -> tuple[Path, Path]:
    features = tmp_path / "features"
    features.mkdir()
    (features / "scoring.feature").write_text(FEATURE)
    junit = tmp_path / "junit.xml"
    junit.write_text(JUNIT)
    return features, junit


def test_needs_verification_scenarios_are_flagged_with_inherited_tags(tmp_path: Path) -> None:
    features, _ = _write(tmp_path)

    rows = collect(features)

    flagged = [r for r in rows if r.needs_verification]
    assert [r.scenario for r in flagged] == ["Receiver wins the rally"]
    assert {"M0", "story-ST-099", "needs-verification"} <= set(flagged[0].tags)


def test_results_come_from_junit(tmp_path: Path) -> None:
    features, junit = _write(tmp_path)

    rows = {r.scenario: r.result for r in collect(features, junit)}

    assert rows == {"Receiver wins the rally": "failed", "Ivy's verified one": "passed"}


def test_render_puts_needs_verification_in_its_own_section(tmp_path: Path) -> None:
    features, junit = _write(tmp_path)

    text = render(collect(features, junit))

    verified, _, unverified = text.partition("## Needs verification")
    assert "Ivy's verified one" in verified
    assert "Receiver wins the rally" in unverified
    assert "Receiver wins the rally" not in verified


def test_scenario_without_junit_result_is_reported_not_run(tmp_path: Path) -> None:
    features, _ = _write(tmp_path)

    assert {r.result for r in collect(features)} == {"not run"}
