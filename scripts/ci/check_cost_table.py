#!/usr/bin/env python3
"""Cost-per-PR table required on a ready ticket PR (CI-DOC-CHECK-06; PRC-11.3; ADR 0056 decision 1).

The pr-policy job runs this on every ready (non-draft) PR. A ticket PR is one whose title starts
with ``[TICKET-ID]``; its ``docs/sprints/<nn>/decisions/<TICKET-ID>.md`` must hold a "Cost per PR"
table with at least one data row (working-agreement §10). A round not captured is written
"not measured" and still counts as a row. The table is read with ``cost_rows`` of
``scripts/measure/flow_metrics.py``, the same reader the sprint cost-table metric uses, so the gate
and the metric agree. A title without a ticket id is not a ticket PR and is skipped.

Usage: PR_TITLE='[ID] title' check_cost_table.py [--title TITLE] [--root DIR]
Labels: logged like every pr-policy step (pr_labels.py); no label waives this check.
Exit codes: 0 table present or not a ticket PR; 1 no decisions file or no table row; 2 usage.
Standard library only.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "measure"))
from flow_metrics import TICKET, cost_rows
from pr_labels import live_labels


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--title", default=os.environ.get("PR_TITLE"), help="PR title (env PR_TITLE)")
    p.add_argument("--root", type=Path, default=Path.cwd())
    a = p.parse_args(argv)
    live_labels(os.environ, "cost-table")  # logs the labels like every pr-policy step
    print("cost-table: no label waives this check")
    if a.title is None:
        print("cost-table: no PR title (--title or PR_TITLE)", file=sys.stderr)
        return 2
    m = TICKET.match(a.title.strip())
    if not m:
        print("cost-table: no [TICKET-ID] title prefix; not a ticket PR; skipped (PRC-11.3)")
        return 0
    ticket, root = m.group(1), a.root.resolve()
    files = sorted((root / "docs" / "sprints").glob(f"*/decisions/{ticket}.md"))
    if not files:
        print(f"FAIL cost-table: no docs/sprints/<nn>/decisions/{ticket}.md (ADR 0056 decision 1)")
        return 1
    # A ticket carried into a later sprint may have a decisions file in each; one table suffices.
    found = {
        path.relative_to(root).as_posix(): cost_rows(path.read_text("utf-8")) for path in files
    }
    with_rows = {rel: rows for rel, rows in found.items() if rows}
    for rel, rows in with_rows.items():
        print(f"cost-table: {rel}: {len(rows)} row(s)")
    if with_rows:
        return 0
    for rel in found:
        print(
            f"FAIL cost-table: {rel} has no 'Cost per PR' table with a row (working-agreement §10)"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
