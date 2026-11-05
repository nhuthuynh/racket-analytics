#!/usr/bin/env python3
"""Browser matrix from Playwright JSON reports (goal scorecard G05-04; NFR-024.1-.3; ST-079).

Each report is a `playwright test --repeat-each 3 --grep @critical --reporter json` run, one per
project (`PW_PROJECTS=<name>`). A required project is ok only when:

* every critical journey ran in it (E2E-04-01..05, sign-in, upload resume; a journey that only
  skipped did not run), as `web/e2e/helpers/critical-journeys.ts` names them;
* every test ran `--repeats` times, and every run passed. Retries are off (NFR-074), so a test
  that passed in one repeat and failed in another is flaky, and flaky fails the project.

    python3 scripts/measure/browser_matrix.py reports/pw-*.json \\
        --require chromium,webkit,android-chrome

Exit 0 when every required project is ok; 1 when one is not, or has no report (fail closed,
ADR 0014); 2 on a malformed report or no `--require`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# (journey id, spec file suffix or None, title pattern or None); the order is the report's.
JOURNEYS: tuple[tuple[str, str | None, re.Pattern[str] | None], ...] = (
    *((f"E2E-04-0{n}", None, re.compile(rf"(?<![\w-])E2E-04-0{n}(?![\d-])")) for n in range(1, 6)),
    ("sign-in", "sprint-01/sign-in.spec.ts", None),
    ("upload-resume", None, re.compile(r"(?<![\w-])E2E-01-02(?![\d-])")),
)

Runs = dict[str, dict[tuple[str, str], list[str]]]


def journey_of(file: str, title: str) -> str | None:
    for jid, suffix, pattern in JOURNEYS:
        if (suffix and file.endswith(suffix)) or (pattern and pattern.search(title)):
            return jid
    return None


def _specs(suite: dict[str, Any]):
    yield from suite.get("specs", [])
    for child in suite.get("suites", []):
        yield from _specs(child)


def collect(reports: list[dict[str, Any]]) -> Runs:
    """project -> (file, title) -> the outcome of each run ("expected", "unexpected", ...)."""
    runs: Runs = {}
    for report in reports:
        for suite in report.get("suites", []):
            for spec in _specs(suite):
                key = (spec["file"], spec["title"])
                for test in spec["tests"]:
                    runs.setdefault(test["projectName"], {}).setdefault(key, []).append(
                        test["status"]
                    )
    return runs


def judge_project(tests: dict[tuple[str, str], list[str]], repeats: int) -> dict[str, Any]:
    passed, failed, flaky, short, skipped, ran = 0, [], [], [], [], set()
    for (file, title), outcomes in tests.items():
        if all(o == "skipped" for o in outcomes):
            skipped.append(title)
            continue
        if len(outcomes) != repeats:
            short.append(f"{title} ({len(outcomes)} of {repeats} runs)")
        if all(o == "expected" for o in outcomes):
            passed += 1
        elif all(o == "unexpected" for o in outcomes):
            failed.append(title)
        else:
            flaky.append(title)
        if jid := journey_of(file, title):
            ran.add(jid)
    missing = [jid for jid, _, _ in JOURNEYS if jid not in ran]
    ok = not (failed or flaky or short or missing)
    return {
        "ok": ok,
        "passed": passed,
        "failed": failed,
        "flaky": flaky,
        "short": short,
        "skipped": skipped,
        "missing": missing,
    }


def judge(runs: Runs, require: list[str], *, repeats: int) -> dict[str, Any]:
    projects: dict[str, Any] = {}
    for name in require:
        projects[name] = (
            judge_project(runs[name], repeats) if name in runs else {"ok": False, "no_report": True}
        )
    return {"ok": all(p["ok"] for p in projects.values()), "repeats": repeats, "projects": projects}


def lines(result: dict[str, Any]) -> list[str]:
    out = []
    for name, p in result["projects"].items():
        if p.get("no_report"):
            out.append(f"{name}: no report")
            continue
        if p["ok"]:
            out.append(f"{name}: ok ({p['passed']} passed x {result['repeats']})")
        out += [f"{name}: missing journey {j}" for j in p["missing"]]
        out += [f"{name}: flaky {t}" for t in p["flaky"]]
        out += [f"{name}: failed {t}" for t in p["failed"]]
        out += [f"{name}: short {t}" for t in p["short"]]
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("reports", nargs="+", type=Path, help="Playwright JSON reports")
    p.add_argument("--require", required=True, help="comma-separated project names")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--json", type=Path)
    args = p.parse_args(argv)
    require = [n.strip() for n in args.require.split(",") if n.strip()]
    if not require:
        print("browser_matrix: --require names no project", file=sys.stderr)
        return 2
    try:
        runs = collect([json.loads(r.read_text(encoding="utf-8")) for r in args.reports])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"browser_matrix: malformed report: {exc}", file=sys.stderr)
        return 2
    result = judge(runs, require, repeats=args.repeats)
    print("\n".join(lines(result)))
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
