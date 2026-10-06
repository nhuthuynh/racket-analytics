#!/usr/bin/env python3
"""Open-loop read latency on the Sprint 2 endpoints (goal scorecard G02-04; NFR-010, NFR-041).

Signs in once (fresh account), creates a doubles match, uploads the fixture, tags the 6-rally
journey (taglib.JOURNEY_TAGS), then sends GET score sheet, GET correction history and
GET /matches/{id} in rotation at ``--rps`` for ``--duration`` seconds on a fixed clock (open
loop, as api_latency.py). Prints p50/p95/p99 and availability (non-5xx / all, excl. 429).

    python3 scripts/measure/tag_latency.py --api http://127.0.0.1:8000 --rps 50 --duration 60 \
        --json reports/goal/tag-latency.json

On the Compose stack the tus Location carries the web's ``/api`` prefix, which the bare API port
does not serve, so seed through the https origin and measure on the API port (SRE-S2-02,
QA-RV1-03):

    python3 scripts/measure/tag_latency.py --api http://127.0.0.1:34800 \
        --seed-api https://localhost:34300/api --origin https://localhost:34300 \
        --cacert <root.crt> --mailpit http://127.0.0.1:34825 --rps 50 --duration 60

Exit 0 only when no response is an unexpected 3xx/4xx (other than 429), p95 <= --max-p95-ms,
p99 <= --max-p99-ms, availability >= --min-availability and the achieved rate is >= 95% of
--rps; 2 when it refuses to start (disk floor).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tagcontract as k
import taglib as t
from live_goal import new_match
from live_tagging import Session, _tag_all, upload_video
from livehttp import Client, sign_in, ssl_context
from measurelib import latency_summary


def _http_url(value: str) -> str:
    if urllib.parse.urlsplit(value).scheme not in ("http", "https"):
        raise argparse.ArgumentTypeError(f"not an http(s) URL: {value!r}")
    return value


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--api", default="http://127.0.0.1:8000", help="API base URL (measured load)")
    p.add_argument(
        "--seed-api",
        type=_http_url,
        help="base URL for the seeding (sign-in, match, upload, tags), e.g. the https origin's "
        "/api; default: --api",
    )
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
    return p


def bases(args: argparse.Namespace) -> tuple[str, str]:
    """(seed base, load base): seeding may go through the origin, the load stays on --api."""
    return (args.seed_api or args.api, args.api)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    seed_base, load_base = bases(args)
    free_gb = shutil.disk_usage("/").free // 1024**3
    if free_gb < args.min_free_gb:
        print(
            f"tag_latency: only {free_gb} GB free on /, need >= {args.min_free_gb} GB; "
            "prune first (bash scripts/disk-precheck.sh, docs/ops/disk-and-prune.md)",
            file=sys.stderr,
        )
        return 2

    ctx = ssl_context(args.cacert, args.insecure_loopback)
    setup = Client(seed_base, args.origin, ctx)
    login = sign_in(setup, args.mailpit)
    match_id = new_match(setup) if login["ok"] else None
    video = (
        upload_video(setup, match_id, Path(args.file).read_bytes(), args.result_timeout)
        if match_id
        else {}
    )
    tagged = (
        _tag_all(Session(setup, match_id), t.JOURNEY_TAGS, "A", check_each=False)
        if video.get("ok")
        else {"ok": False}
    )
    if not tagged["ok"]:
        print(
            json.dumps({"ok": False, "sign_in": login, "video": video, "tagged": tagged}),
            file=sys.stderr,
        )
        return 1
    cookie = setup.cookie
    setup.close()
    paths = [
        k.path("sheet", match_id=match_id)[1],
        k.path("history", match_id=match_id)[1],
        f"/matches/{match_id}",
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
            local.c = Client(load_base, args.origin, ctx, timeout=10)
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
        api=load_base,
        seed_api=seed_base,
        endpoints=paths,
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
