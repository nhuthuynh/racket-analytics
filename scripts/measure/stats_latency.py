#!/usr/bin/env python3
"""Open-loop read latency on the Sprint 3 stats endpoints (goal scorecard G03-05; NFR-010).

Signs in once (fresh account), creates a doubles match, uploads the fixture, tags the coach's
worked example (statslib.STATS_TAGS), waits until the stats equal the reference, then sends
GET stats, GET evidence (AN-01, side A) and GET /matches/{id} in rotation at ``--rps`` for
``--duration`` seconds on a fixed clock (open loop, as tag_latency.py). Seeding goes through
the https origin (``--seed-api``), the load through the API port (``--api``) (SRE-S2-02).

Exit 0 only when no response is an unexpected 3xx/4xx (other than 429), p95 <= --max-p95-ms,
p99 <= --max-p99-ms, availability >= --min-availability and the achieved rate is >= 95% of
--rps; 1 when seeding fails; 2 when it refuses to start (disk floor).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import statscontract as sk
import statslib as s
import tagcontract as k
from live_goal import new_match
from live_stats import _poll_stats, _reference
from live_tagging import Session, upload_video
from livehttp import Client, sign_in, ssl_context
from measurelib import latency_summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--api", default="http://127.0.0.1:8000", help="API base (measured load)")
    p.add_argument("--seed-api", help="API base for sign-in, upload and tagging (default --api)")
    p.add_argument("--origin", default="https://localhost:3000")
    p.add_argument("--mailpit", default="http://127.0.0.1:8025")
    p.add_argument("--cacert")
    p.add_argument("--insecure-loopback", action="store_true")
    p.add_argument("--file", default="fixtures/clips/synthetic-60s/clip.mp4")
    p.add_argument("--rps", type=float, default=50.0)
    p.add_argument("--duration", type=float, default=60.0)
    p.add_argument("--workers", type=int, default=64)
    p.add_argument("--max-p95-ms", type=float, default=300.0)
    p.add_argument("--max-p99-ms", type=float, default=800.0)
    p.add_argument("--min-availability", type=float, default=0.995)
    p.add_argument("--result-timeout", type=float, default=120.0)
    p.add_argument("--json", type=Path)
    p.add_argument("--min-free-gb", type=int, default=10)
    args = p.parse_args(argv)

    free_gb = shutil.disk_usage("/").free // 1024**3
    if free_gb < args.min_free_gb:
        print(
            f"stats_latency: only {free_gb} GB free on /, need >= {args.min_free_gb} GB; "
            "prune first (bash scripts/disk-precheck.sh, docs/ops/disk-and-prune.md)",
            file=sys.stderr,
        )
        return 2

    ctx = ssl_context(args.cacert, args.insecure_loopback)
    setup = Client(args.seed_api or args.api, args.origin, ctx)
    login = sign_in(setup, args.mailpit)
    match_id = new_match(setup) if login["ok"] else None
    video = (
        upload_video(setup, match_id, Path(args.file).read_bytes(), args.result_timeout)
        if match_id
        else {}
    )
    seeded = bool(video.get("ok"))
    if seeded:
        sess = Session(setup, match_id)
        sess.call("start_game", {**k.START_GAME_BODY, "first_serving_side": "A"})
        seeded = all(sess.call("tag", tag).status == 201 for tag in s.STATS_TAGS)
    if seeded:
        ms, _ = _poll_stats(setup, match_id, _reference(s.STATS_TAGS), args.result_timeout)
        seeded = ms is not None
    if not seeded:
        print(json.dumps({"ok": False, "sign_in": login, "video": video}), file=sys.stderr)
        return 1
    cookie = setup.cookie
    setup.close()
    paths = [
        sk.path("stats", match_id=match_id)[1],
        sk.path("evidence", match_id=match_id, metric_id="AN-01", side="A")[1],
        sk.path("match", match_id=match_id)[1],
    ]

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
    summary.update(target_rps=args.rps, duration_s=args.duration, api=args.api, endpoints=paths)
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
