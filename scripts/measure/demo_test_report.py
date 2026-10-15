#!/usr/bin/env python3
"""Sprint demo step 10 test report (sprint-03 §12; goal metric DEMO-03; FIX-03-2d).

    demo_test_report.py --reports reports/goal03-verify-r2 \\
        --ledger docs/sprints/03/review-rounds.md --scorecard docs/sprints/03/goal-scorecard.md

One line per item. Exit 0 only when every item passes; 1 when any fails (a missing report
fails its item); 2 when the ledger or the scorecard is unreadable (fail closed, ADR 0014).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measurelib import junit_rate, open_defects

MUTATION_TARGETS = (
    ("mutation rules", "mutation-rules.json", 0.85),
    ("mutation starter stats", "mutation-stats.json", 0.80),
)
PROPERTY_MIN = 1000
_TOTALS = re.compile(r"\*\*Totals: (\d+) of (\d+) met")
_PROPERTY = re.compile(r"(\d+) passing, (\d+) failing")


def _item(item: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"item": item, "ok": ok, "detail": detail}


def _json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _rate(reports: Path, item: str, name: str) -> dict[str, Any]:
    r = _json(reports / name)
    if r is None:
        return _item(item, False, f"{item}: missing {name}")
    ok = r.get("ok") is True and r.get("rate") == 1.0 and not r.get("failed")
    return _item(item, ok, f"{item}: {r.get('passed')}/{r.get('selected')} passed")


def _conservation(reports: Path) -> dict[str, Any]:
    item = "conservation property"
    rate = _rate(reports, item, "conservation-rate.json")
    path = reports / "conservation-property.txt"
    found = _PROPERTY.search(path.read_text("utf-8")) if path.is_file() else None
    if found is None:
        return _item(item, False, f"{item}: no Hypothesis statistics in {path.name}")
    passing, failing = int(found[1]), int(found[2])
    ok = rate["ok"] and passing >= PROPERTY_MIN and failing == 0
    return _item(item, ok, f"{item}: {passing} passing, {failing} failing")


def _mutation(reports: Path, item: str, name: str, target: float) -> dict[str, Any]:
    summary = _json(reports / name)
    if summary is None:
        return _item(item, False, f"{item}: missing {name}")
    score = summary.get("score")
    ok = summary.get("status") == "measured" and isinstance(score, float) and score >= target
    return _item(item, ok, f"{item}: {score} (target ≥ {target})")


def _crawl(reports: Path) -> dict[str, Any]:
    item = "evidence crawl"
    try:
        rate = junit_rate([reports / "e2e.xml"], "E2E-03-02")
    except (OSError, ValueError) as exc:
        return _item(item, False, f"{item}: e2e.xml unreadable ({exc.__class__.__name__})")
    return _item(item, rate["ok"], f"{item}: E2E-03-02 {rate['passed']}/{rate['selected']} passed")


def step10_report(reports: Path, ledger_text: str, scorecard_text: str) -> dict[str, Any]:
    """Every step 10 item; raises ValueError when the ledger or the scorecard is unreadable."""
    totals = _TOTALS.findall(scorecard_text)
    if not totals:
        raise ValueError("scorecard has no Totals line")
    met, of = (int(n) for n in totals[-1])
    defects = open_defects(ledger_text)
    named = f" ({', '.join(row['ids'][0] for row in defects)})" if defects else ""
    items = [
        _item("scorecard", met == of and of > 0, f"scorecard: {met} of {of} met"),
        _rate(reports, "golden matches", "golden-an-rate.json"),
        _conservation(reports),
        *(_mutation(reports, *target) for target in MUTATION_TARGETS),
        _crawl(reports),
        _item("open defects", not defects, f"open defects: {len(defects)}{named}"),
    ]
    return {"ok": all(i["ok"] for i in items), "items": items}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reports", type=Path, required=True, help="verifier report directory")
    parser.add_argument("--ledger", type=Path, required=True, help="review-rounds Markdown")
    parser.add_argument("--scorecard", type=Path, required=True, help="goal scorecard Markdown")
    parser.add_argument("--json", type=Path, help="also write the result here")
    args = parser.parse_args(argv)
    try:
        result = step10_report(
            args.reports, args.ledger.read_text("utf-8"), args.scorecard.read_text("utf-8")
        )
    except (OSError, ValueError) as exc:
        print(f"demo_test_report: {exc}", file=sys.stderr)
        return 2
    for i in result["items"]:
        print(("ok    " if i["ok"] else "FAIL  ") + i["detail"])
    print("step 10: " + ("passes" if result["ok"] else "fails"))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
