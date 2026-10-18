"""``racket-plan-eval``: the code-grader eval on rules-only plans (ST-060; NFR-005 a; G04-04).

    racket-plan-eval [--runs 3] [--cases DIR] [--library DIR] [--min-cases 30] [--json PATH]

Prints one ``PASS``/``FAIL`` line per case and a ``pass^N`` summary. Exit 0 when every case
passes all runs with byte-identical output and the set has at least ``--min-cases`` cases; 1 on
any failure; 2 when the cases or the library cannot be read. Defaults: the repository's
``backend/tests/evals/plan_cases`` and ``content/drills``, found from the working directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from racket.coaching.evals.cases import CaseError, load_cases
from racket.coaching.evals.library import find_repo, load_library
from racket.coaching.evals.runner import evaluate

MIN_CASES = 30  # NFR-005a, sprint-04 ST-060


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="racket-plan-eval", description=__doc__.splitlines()[0])
    ap.add_argument("--runs", type=int, default=3, help="runs per case (pass^N), default 3")
    ap.add_argument("--cases", type=Path, help="eval case directory")
    ap.add_argument("--library", type=Path, help="drill library directory (content/drills)")
    ap.add_argument("--min-cases", type=int, default=MIN_CASES)
    ap.add_argument("--json", type=Path, help="write the per-case report here")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo = find_repo(Path.cwd().resolve())
    cases_dir = args.cases or (
        repo / "backend" / "tests" / "evals" / "plan_cases" if repo else None
    )
    library_dir = args.library or (repo / "content" / "drills" if repo else None)
    if cases_dir is None or library_dir is None:
        print("racket-plan-eval: no repository found; pass --cases and --library", file=sys.stderr)
        return 2
    try:
        cases = load_cases(cases_dir)
        library = load_library(library_dir)
        report = evaluate(cases, library, runs=args.runs, min_cases=args.min_cases)
    except (CaseError, OSError, ValueError) as exc:
        print(f"racket-plan-eval: {exc}", file=sys.stderr)
        return 2
    print("\n".join(report.lines()))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report.as_json(), indent=2) + "\n", encoding="utf-8")
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
