"""The SIZE-WAIVERS-03 scope: Sprint 3 ticket PRs over 400 changed lines with their decisions file.

Values are the ticket's measurement (2026-10-08); DOCS-03 is the record paths measured with
`git diff --numstat origin/main...origin/sprint-03 -- docs/...` (6,235 lines).
"""

from __future__ import annotations

from conftest import REPO_ROOT

DECISIONS = REPO_ROOT / "docs" / "sprints" / "03" / "decisions" / "SIZE-WAIVERS-03.md"
SCOPE = {
    "HARNESS-03": 1462,
    "ST-043": 496,
    "ST-044": 828,
    "ST-045": 428,
    "ST-049": 575,
    "COACH-1": 1530,
    "QA-ACC-3": 3160,
    "ST-053": 1026,
    "ST-052a": 558,
    "PE-R1S3-07": 585,
    "SRE-PURGE-a": 516,
    "ST-042": 894,
    "PE-DESIGN-3": 936,
    "ST-048": 2316,
    "ST-050": 412,
    "ST-050b": 892,
    "ST-052": 1444,
    "DOCS-03": 6235,
    "SIZE-WAIVERS-03": 552,  # this ticket's own PR #6, without this decisions file
}
