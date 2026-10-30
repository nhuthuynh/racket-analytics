#!/usr/bin/env python3
"""Write the nightly quality results into the sprint status file (ST-024; sprint-01 §14.3.8).

Sets the ``nightly`` key (``STATUS_NIGHTLY_KEY`` in backend/tests/support/contract.py) of
``docs/sprints/<NN>/status.json`` and leaves every other key untouched:

    nightly:
      run_date, run_url, commit
      oracle:   status passed|failed|no_report, sequences, disagreements, seed, shortest, job
      mutation: status measured|target_missing|no_mutants|not_checked|no_stats|no_report,
                score (0..1), scope, killed, survived, total, ..., job
      mutation_scopes: {scope: the same entry, plus min_score and gate passed|failed}, one per
                ``--mutation-scope SCOPE=PATH`` (coaching/plan, coaching/weakness; sprint-04 §8)

A missing or unreadable report is recorded as ``no_report`` (never as passed). ``--status auto``
picks the highest-numbered ``docs/sprints/NN/status.json`` under the working directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ORACLE_KEYS = ("sequences", "disagreements", "seed", "seconds", "shortest")


def find_status(root: Path) -> Path:
    candidates = sorted(
        p for p in root.glob("docs/sprints/[0-9][0-9]/status.json") if p.parent.name.isdigit()
    )
    if not candidates:
        raise SystemExit("nightly_status: no docs/sprints/NN/status.json found")
    return candidates[-1]


def _load(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def oracle_entry(report: dict[str, Any] | None, job: str | None) -> dict[str, Any]:
    if report is None:
        entry: dict[str, Any] = {"status": "no_report"}
    else:
        entry = {"status": "passed" if report.get("passed") is True else "failed"}
        entry.update({k: report.get(k) for k in ORACLE_KEYS})
        entry["passed"] = report.get("passed") is True
    if job:
        entry["job"] = job
    return entry


def mutation_entry(report: dict[str, Any] | None, job: str | None) -> dict[str, Any]:
    entry = {"status": "no_report", "score": None} if report is None else dict(report)
    if job:
        entry["job"] = job
    return entry


def scope_arg(text: str) -> tuple[str, Path]:
    scope, sep, path = text.partition("=")
    if not (sep and scope and path):
        raise argparse.ArgumentTypeError(f"expected SCOPE=PATH, got {text!r}")
    return scope, Path(path)


def scope_entry(scope: str, report: dict[str, Any] | None, job: str | None) -> dict[str, Any]:
    entry = mutation_entry(report, job)
    entry.setdefault("scope", scope)
    if report is None:
        entry["gate"] = "failed"  # a gate with no report never passes
    return entry


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--status", required=True, help="status.json path, or 'auto'")
    p.add_argument("--oracle", type=Path)
    p.add_argument("--mutation", type=Path)
    p.add_argument("--oracle-job", help="result of the oracle job (success, failure, ...)")
    p.add_argument("--mutation-job", help="result of the mutation job")
    p.add_argument(
        "--mutation-scope",
        type=scope_arg,
        action="append",
        default=[],
        metavar="SCOPE=PATH",
        help="a further gated mutation report, by scope",
    )
    p.add_argument("--date", default=dt.datetime.now(dt.UTC).date().isoformat())
    p.add_argument("--run-url", required=True)
    p.add_argument("--sha", required=True)
    a = p.parse_args(argv)

    path = find_status(Path.cwd()) if a.status == "auto" else Path(a.status)
    data = json.loads(path.read_text())
    data["nightly"] = {
        "run_date": a.date,
        "run_url": a.run_url,
        "commit": a.sha,
        "oracle": oracle_entry(_load(a.oracle), a.oracle_job),
        "mutation": mutation_entry(_load(a.mutation), a.mutation_job),
    }
    if a.mutation_scope:
        data["nightly"]["mutation_scopes"] = {
            scope: scope_entry(scope, _load(path), a.mutation_job)
            for scope, path in a.mutation_scope
        }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"nightly_status: wrote {path}")
    print(json.dumps(data["nightly"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
