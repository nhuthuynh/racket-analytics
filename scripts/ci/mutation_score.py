#!/usr/bin/env python3
"""Mutation score for one package (ST-024, NFR-072; tool mutmut per ADR 0008).

Run mode (nightly): writes a temporary ``setup.cfg`` [mutmut] section in ``--project``, runs
``mutmut run`` and ``mutmut export-cicd-stats``, then removes the file again. mutmut must be on
PATH (the workflow uses ``uv run --with mutmut==<pin>``).

    mutation_score.py --project backend --target src/racket/sports/pickleball/rules \
        --tests tests/unit/sports \
        --ignore tests/unit/sports/pickleball/test_rules_static.py --out reports/mutation.json

``--ignore PATH`` keeps a test file out of every mutmut pytest run (``pytest --ignore``). Use it
for tests that scan the source text, such as the IT-01-13 import check: mutmut 3 adds a
``mutmut`` import to every mutated file, so such a test fails on the instrumented copy and mutmut
stops at "failed to collect stats" (PE-R1-S1-01). Those tests still run in the normal suite.

``--from-stats FILE`` scores an existing ``mutmut-cicd-stats.json`` instead (tests, reruns).

Score = (killed + timeout) / (total - skipped). Mutants with no covering test count as
survivors. Fails closed: a missing target or zero mutants is exit 1, never a pass.
Sprint 1 records a baseline; the >= 85% gate starts in Sprint 2 (``--min-score``).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

STATS_FILE = Path("mutants") / "mutmut-cicd-stats.json"


def scope_of(target: str) -> str:
    """``src/racket/sports/pickleball/rules`` -> ``sports/pickleball/rules`` (contract name)."""
    parts = [p for p in target.strip("/").split("/") if p]
    while parts and parts[0] in ("src", "racket"):
        parts.pop(0)
    return "/".join(parts)


def score(stats: dict[str, Any], target: str) -> dict[str, Any]:
    killed, timeout = int(stats.get("killed", 0)), int(stats.get("timeout", 0))
    total, skipped = int(stats.get("total", 0)), int(stats.get("skipped", 0))
    base = total - skipped
    report: dict[str, Any] = {
        "target": target,
        "scope": scope_of(target),
        "killed": killed,
        "timeout": timeout,
        "survived": int(stats.get("survived", 0)),
        "no_tests": int(stats.get("no_tests", 0)),
        "suspicious": int(stats.get("suspicious", 0)),
        "skipped": skipped,
        "total": total,
        "tool": "mutmut",
    }
    if base <= 0:
        return {**report, "status": "no_mutants", "score": None}
    checked = sum(report[k] for k in ("killed", "timeout", "survived", "no_tests", "suspicious"))
    if checked == 0:  # mutants generated but none tested (e.g. the test run itself failed)
        return {**report, "status": "not_checked", "score": None}
    return {**report, "status": "measured", "score": round((killed + timeout) / base, 4)}


def run_mutmut(
    project: Path, target: str, tests: list[str], ignore: list[str] | None = None
) -> dict[str, Any] | None:
    cfg = project / "setup.cfg"
    if cfg.exists():
        print(f"mutation_score: {cfg} exists; refusing to overwrite it", file=sys.stderr)
        raise SystemExit(2)

    # mutmut 3 runs the tests inside ./mutants, which holds only what it copies (tests/ is
    # copied by default): the rest of src/, which the target imports, goes in also_copy.
    # setup.cfg lists are newline-separated continuation lines.
    def as_list(items: list[str]) -> str:
        return "".join(f"\n    {item.rstrip('/')}/" for item in items)

    text = (
        "[mutmut]\n"
        f"source_paths ={as_list([target])}\n"
        f"pytest_add_cli_args_test_selection ={as_list(tests)}\n"
        f"also_copy ={as_list(['src'])}\n"
    )
    if ignore:
        text += "pytest_add_cli_args =" + "".join(f"\n    --ignore={p}" for p in ignore) + "\n"
    cfg.write_text(text)
    stats = project / STATS_FILE
    # A stats file from an earlier run must never be read as this run's result (QA-V1-03).
    stats.unlink(missing_ok=True)
    try:
        subprocess.run(["mutmut", "run"], cwd=project, check=False)
        subprocess.run(["mutmut", "export-cicd-stats"], cwd=project, check=False)
    finally:
        cfg.unlink(missing_ok=True)
    return json.loads(stats.read_text()) if stats.is_file() else None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", type=Path, default=Path())
    p.add_argument("--target", required=True)
    p.add_argument("--tests", action="append", default=[])
    p.add_argument("--ignore", action="append", default=[])
    p.add_argument("--from-stats", type=Path)
    p.add_argument("--min-score", type=float)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)

    if a.from_stats is not None:
        stats: dict[str, Any] | None = json.loads(a.from_stats.read_text())
    elif not (a.project / a.target).exists():
        report = {
            "target": a.target,
            "scope": scope_of(a.target),
            "status": "target_missing",
            "score": None,
        }
        a.out.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
        return 1
    else:
        stats = run_mutmut(a.project, a.target, a.tests or ["tests"], a.ignore)

    if stats is None:
        report = {
            "target": a.target,
            "scope": scope_of(a.target),
            "status": "no_stats",
            "score": None,
        }
    else:
        report = score(stats, a.target)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if report["score"] is None:
        return 1
    if a.min_score is not None and report["score"] < a.min_score:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
