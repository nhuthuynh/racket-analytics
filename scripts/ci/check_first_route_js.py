#!/usr/bin/env python3
"""First-route JS budget (NFR-015): gzipped JS for the first route <= budget.

Reads Next.js build manifests: rootMainFiles (build-manifest.json) plus the route's chunks
(app-build-manifest.json, App Router). Polyfills are excluded (served only to legacy
browsers via nomodule). Each file is counted once.
Usage: check_first_route_js.py --next-dir web/.next [--route /page] --budget-kb 200
Exit: 0 within budget, 1 over budget, 2 build output missing (fails closed).
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--next-dir", required=True)
    ap.add_argument("--route", default="/page")
    ap.add_argument("--budget-kb", type=float, required=True)
    args = ap.parse_args(argv)
    nxt = Path(args.next_dir)
    try:
        build = json.loads((nxt / "build-manifest.json").read_text())
        app = json.loads((nxt / "app-build-manifest.json").read_text())
        route_files = app["pages"][args.route]
    except (OSError, ValueError, KeyError) as exc:
        print(
            f"first-route-js: cannot read Next.js build output in {nxt} ({exc!r}); run "
            "`next build` first. Failing closed."
        )
        return 2
    polyfills = set(build.get("polyfillFiles", []))
    files = [
        f
        for f in dict.fromkeys([*build.get("rootMainFiles", []), *route_files])
        if f.endswith(".js") and f not in polyfills
    ]
    total = 0
    for f in files:
        size = len(gzip.compress((nxt / f).read_bytes(), compresslevel=9))
        total += size
        print(f"  {size / 1024:8.1f} KB  {f}")
    kb = total / 1024
    verdict = "within budget" if kb <= args.budget_kb else "over budget"
    print(
        f"first-route-js: {args.route} loads {kb:.1f} KB gzipped JS; {verdict} "
        f"({args.budget_kb:g} KB, NFR-015)"
    )
    return 0 if kb <= args.budget_kb else 1


if __name__ == "__main__":
    sys.exit(main())
