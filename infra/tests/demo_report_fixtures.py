"""FIX-03-2d fixtures: a verifier report directory in the verifier's formats, a ledger and a
goal scorecard."""

from __future__ import annotations

import json
from pathlib import Path

RATE_OK = '{"selected": 2, "passed": 2, "failed": 0, "rate": 1.0, "ok": true}'
CRAWL = "@M0 @story-ST-047 @nfr-038 Evidence crawl \u203a E2E-03-02 every metric shows n"
GOOD = {"rules": 0.8635, "stats": 0.8977, "passing": 1000, "failing": 0, "crawl_failed": False}


def report_dir(path: Path, **kw: float) -> Path:
    v = {**GOOD, **kw}
    path.mkdir(parents=True, exist_ok=True)
    files = {"golden-an-rate.json": RATE_OK, "conservation-rate.json": RATE_OK}
    for name, key in (("mutation-rules.json", "rules"), ("mutation-stats.json", "stats")):
        files[name] = json.dumps({"status": "measured", "killed": 9, "score": v[key]})
    files["conservation-property.txt"] = (
        f"    - {v['passing']} passing, {v['failing']} failing, and 71 invalid test cases\n"
    )
    failure = '<failure message="no Show me"/>' if v["crawl_failed"] else ""
    files["e2e.xml"] = (
        f'<testsuites><testsuite name="s"><testcase name="{CRAWL}" classname="e2e">{failure}'
        '</testcase><testcase name="E2E-03-01 journey" classname="e2e"/></testsuite></testsuites>'
    )
    for name, text in files.items():
        (path / name).write_text(text, encoding="utf-8")
    return path


def ledger(*open_rows: tuple[str, str]) -> str:
    rows = "| PE-R1S3-01 | blocker | Fixed. Merged | pr |\n"
    rows += "".join(f"| {i} | {sev} | Open. Waits on another role | — |\n" for i, sev in open_rows)
    return "| Id | Severity | Disposition | Evidence |\n|---|---|---|---|\n" + rows


def scorecard(met: int, of: int = 12) -> str:
    return f"**Totals: 2 of {of} met** (round 1).\n\n**Totals: {met} of {of} met** (latest).\n"
