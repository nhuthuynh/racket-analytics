"""Fixtures for the demo step 10 report (FIX-03-2d): a verifier report directory in the
formats the goal verifier writes (junit_rate JSON, mutmut summary JSON, Hypothesis statistics
text, Playwright JUnit XML), a review-rounds ledger and a goal scorecard."""

from __future__ import annotations

import json
from pathlib import Path

RATE_OK = {"selected": 2, "passed": 2, "failed": 0, "skipped": 0, "rate": 1.0, "missing": [],
           "failures": [], "ok": True}
CRAWL = "@M0 @story-ST-047 @nfr-038 Evidence crawl › E2E-03-02 every metric shows n"


def report_dir(path: Path, *, crawl_failed: bool = False, rules: float = 0.8635,
               stats: float = 0.8977, passing: int = 1000, failing: int = 0) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    for name in ("golden-an-rate.json", "conservation-rate.json"):
        (path / name).write_text(json.dumps(RATE_OK), encoding="utf-8")
    for name, score in (("mutation-rules.json", rules), ("mutation-stats.json", stats)):
        summary = {"status": "measured", "killed": 9, "total": 10, "score": score}
        (path / name).write_text(json.dumps(summary), encoding="utf-8")
    (path / "conservation-property.txt").write_text(
        f"  - during generate phase (4.40 seconds):\n    - {passing} passing, {failing} failing,"
        " and 71 invalid test cases\n\n1 passed, 12 deselected in 4.47s\n", encoding="utf-8")
    failure = '<failure message="no Show me"/>' if crawl_failed else ""
    (path / "e2e.xml").write_text(
        f'<testsuites><testsuite name="crawl"><testcase name="{CRAWL}" classname="e2e">'
        f'{failure}</testcase><testcase name="E2E-03-01 journey" classname="e2e"/>'
        "</testsuite></testsuites>", encoding="utf-8")
    return path


HEADER = "| Id | Severity | Disposition | Evidence |\n|---|---|---|---|\n"


def ledger(*open_rows: tuple[str, str]) -> str:
    rows = "| PE-R1S3-01 | blocker | Fixed. Merged | pr |\n"
    rows += "".join(f"| {i} | {sev} | Open. Waits on another role | — |\n" for i, sev in open_rows)
    return "# Review rounds\n\n" + HEADER + rows


def scorecard(met: int, of: int = 12) -> str:
    return (f"# Goal scorecard\n\n**Totals: 2 of {of} met** (round 1).\n\n"
            f"## Round 2\n\n**Totals: {met} of {of} met** (latest).\n")
