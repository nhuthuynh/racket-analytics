#!/usr/bin/env python3
"""Open-loop API read latency at a fixed request rate (goal scorecard G01-04; NFR-010, NFR-041).

Signs in once by magic link (fresh account), creates one doubles match, then sends GET
/matches/{id}, GET /matches and GET /me in rotation at ``--rps`` for ``--duration`` seconds
from a thread pool. Requests are scheduled on a fixed clock (open loop), so a slow server
cannot lower the offered rate. Prints p50/p95/p99 and availability (non-5xx / all, excl. 429).

    python3 scripts/measure/api_latency.py --api http://127.0.0.1:8000 --rps 50 --duration 60 \
        --json reports/goal/api-latency.json

Exit 0 only when no response is an unexpected 3xx/4xx (other than 429), p95 <= --max-p95-ms,
p99 <= --max-p99-ms, availability >= --min-availability and the achieved rate is >= 95% of --rps.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_goal import new_match
from livehttp import Client, sign_in, ssl_context
from measurelib import latency_summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--api", default="http://127.0.0.1:8000", help="API base URL (server-side)")
    p.add_argument("--origin", default="https://localhost:3000")
    p.add_argument("--mailpit", default="http://127.0.0.1:8025")
    p.add_argument("--cacert")
    p.add_argument("--insecure-loopback", action="store_true")
    p.add_argument("--rps", type=float, default=50.0)
    p.add_argument("--duration", type=float, default=60.0, help="seconds")
    p.add_argument("--workers", type=int, default=64)
    p.add_argument("--max-p95-ms", type=float, default=300.0)
    p.add_argument("--max-p99-ms", type=float, default=800.0)
    p.add_argument("--min-availability", type=float, default=0.995)
    p.add_argument("--json", type=Path)
    args = p.parse_args(argv)

    ctx = ssl_context(args.cacert, args.insecure_loopback)
    setup = Client(args.api, args.origin, ctx)
    login = sign_in(setup, args.mailpit)
    match_id = new_match(setup) if login["ok"] else None
    if not match_id:
        print(json.dumps({"ok": False, "sign_in": login, "match_id": match_id}), file=sys.stderr)
        return 1
    cookie = setup.cookie
    setup.close()
    paths = [f"/matches/{match_id}", "/matches", "/me"]

    local = threading.local()
    lock = threading.Lock()
    latencies: list[float] = []
    statuses: list[int] = []

    def fire(i: int, due: float) -> None:
        delay = due - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        if not hasattr(local, "c"):
            local.c = Client(args.api, args.origin, ctx, timeout=10)
            local.c.cookie = cookie
        try:
            r = local.c.request("GET", paths[i % len(paths)])
            status, ms = r.status, r.ms
        except OSError:
            status, ms = 0, None
        with lock:
            statuses.append(status)
            if ms is not None and status < 500 and status != 429:
                latencies.append(ms)

    total = int(args.rps * args.duration)
    start = time.perf_counter() + 0.5
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i in range(total):
            pool.submit(fire, i, start + i / args.rps)
    wall = time.perf_counter() - start
    summary = latency_summary(latencies, statuses, wall)
    summary.update(
        target_rps=args.rps,
        duration_s=args.duration,
        api=args.api,
        endpoints=["GET /matches/{id}", "GET /matches", "GET /me"],
    )
    summary["ok"] = bool(
        summary["p95_ms"] is not None
        and summary["p95_ms"] <= args.max_p95_ms
        and summary["p99_ms"] <= args.max_p99_ms
        and summary["availability"] >= args.min_availability
        and summary["status_unexpected"] == 0
        and summary["achieved_rps"] >= 0.95 * args.rps
    )
    text = json.dumps(summary, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
