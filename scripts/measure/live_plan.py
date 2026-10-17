#!/usr/bin/env python3
"""Live Sprint 4 goal journey: the rules-only plan (goal scorecard G04-01, G04-02, G04-03 a/d).

Each run is a fresh account over https through the web origin (ADR 0029): sign in, a doubles
match, the fixture by tus, the coach's worked example tagged (stats = statslib); POST /me/plan
--generations times (timed, G04-02 a; the first --determinism k bodies identical, G04-03 d); the
ranking = planlib (step 4); planlib.grade (QD-PL-01..03, step 5); citations = GET stats and
evidence (QD-PL-04, step 6); limited data (QD-PL-06, step 7); done twice with one
Idempotency-Key, timed until GET shows it (step 8, G04-02 b); "Not for me" (step 9); 404s for a
second account (step 10). The reference check compares planlib with the catalogue's worked
examples (G04-03 a). --load: GET /me/plan open loop at --rps for --duration (G04-02 c).

    python3 scripts/measure/live_plan.py --base-url https://localhost:43000 --cacert ca.crt \
        --mailpit http://127.0.0.1:48025 --runs 5 --determinism 3 --json live-plan.json

Exit 0 only when every step of every run passed and every target was met; 1 on any failed step;
2 when it refuses to start (disk floor; stack, fixture or drill library unreadable). Routes and
fields: docs/architecture/api-sprint-04.md (PE-4); a contract change changes this file.
"""

from __future__ import annotations

import argparse
import http.client
import json
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planlib as pl
import statscontract as sk
import statslib as s
import tagcontract as k
import taglib as t
from live_goal import new_match
from live_stats import _poll_stats, _reference, sign_in_as
from live_tagging import Session, upload_video
from livehttp import Client, ssl_context
from measurelib import latency_summary

REPO = Path(__file__).resolve().parents[2]
SIDE = "A"  # Ivy is A1 (live_goal.DOUBLES)
PREFS = {"minutes_per_session": 30, "sessions_per_week": 3, "players_available": 1}
PREFS |= {"equipment": ["wall"], "level": "intermediate"}
VOLATILE = {"id", "version", "created_at", "done", "done_at", "regenerated", "plan_version"}


def content(body: Any) -> Any:
    """The plan without ids, version, clock and done state (coaching-plan §6.5)."""
    if isinstance(body, dict):
        return {x: v if x == "drill" else content(v) for x, v in body.items() if x not in VOLATILE}
    return [content(v) for v in body] if isinstance(body, list) else body


def step(problems: list[str], **extra: Any) -> dict[str, Any]:
    return {"ok": not problems, "problems": problems[:20], **extra}


def evidence_ids(c: Client, match_id: str, metric_id: str) -> set[str]:
    ids, cursor = set(), None
    for _ in range(100):
        p = sk.path("evidence", match_id=match_id, metric_id=metric_id, side=SIDE)[1]
        r = c.request("GET", p + (f"&cursor={cursor}" if cursor else ""))
        body = r.json() if r.status == 200 else {}
        ids |= {i.get(sk.EVIDENCE_RALLY_ID) for i in body.get(sk.EVIDENCE_ITEMS) or []}
        if not (cursor := body.get("next_cursor")):
            break
    return ids


def seed(args: argparse.Namespace, ctx: Any, steps: dict) -> tuple[Client, str | None, dict]:
    """Steps 1-2: a fresh account with the worked example tagged and its stats current."""
    c = Client(args.api, args.origin, ctx)
    ok = sign_in_as(c, args.mailpit, f"goal04-{uuid.uuid4().hex[:12]}@example.com")
    match_id = new_match(c) if ok else None
    video = upload_video(c, match_id, args.data, args.result_timeout) if match_id else {}
    steps["setup"] = step([] if video.get("ok") else [f"setup: {video}"])
    if not video.get("ok"):
        return c, None, {}
    sess = Session(c, match_id)
    sess.call("start_game", {**k.START_GAME_BODY, "first_serving_side": "A"})
    codes = [sess.call("tag", tag).status for tag in s.STATS_TAGS]
    _, diffs = _poll_stats(c, match_id, _reference(s.STATS_TAGS), args.result_timeout)
    stats = c.request(*sk.path("stats", match_id=match_id)).json() or {}
    if stats.get("unofficial") is not True or stats.get("label") != t.UNOFFICIAL_LABEL:
        diffs.append(f"unofficial label missing: {stats.get('label')!r}")
    diffs += [f"tag status {x}" for x in set(codes) - {201}]
    steps["stats"] = step(diffs)
    return c, match_id if not diffs else None, stats


def run(args: argparse.Namespace, ctx: Any, library: dict, out: dict) -> dict[str, Any]:
    steps: dict[str, Any] = {}
    c, match_id, stats = seed(args, ctx, steps)
    if not match_id:
        return steps
    bodies = []
    for _ in range(max(args.generations, args.determinism)):
        r = c.request("POST", "/me/plan", json_body=PREFS)
        bodies.append(r.json() if r.status == 201 else None)
        out["generate_ms"] += [r.ms] if r.status == 201 else []
    plan = bodies[-1] or {}
    steps["generate"] = step([f"{bodies.count(None)} of {len(bodies)} not 201"] * (None in bodies))
    if None in bodies:
        return steps
    same = {json.dumps(content(b), sort_keys=True) for b in bodies[: args.determinism]}
    digests = {b.get("content_digest") for b in bodies[: args.determinism]}
    steps["determinism"] = step(
        [f"plan differs across {args.determinism} generations"] * (len(same) + len(digests) > 2)
    )
    want = pl.ranking([{"first_serving_side": "A", "tags": s.STATS_TAGS}], SIDE)
    steps["ranking"] = step(pl.ranking_problems(want, plan.get("ranking")))
    got = plan.get("preferences") or {}
    prefs = [f"preferences {x}: {got.get(x)!r}" for x, v in PREFS.items() if got.get(x) != v]
    steps["plan_rules"] = step(prefs + pl.grade(plan, library))
    cited = {
        a["citation"]["metric_id"]
        for x in plan["sessions"]
        for a in x["assignments"]
        if a.get("citation")
    }
    ev = {m: evidence_ids(c, match_id, m) for m in cited}
    steps["citations"] = step(pl.citation_problems(plan, stats, SIDE, ev, library))
    limited = plan.get("limited_data")
    steps["limited_data"] = step(
        [f"limited_data {limited!r}"] * (limited != {"rallies": want["rallies"]})
    )

    if not plan.get("sessions"):
        return steps
    first, last = plan["sessions"][0], plan["sessions"][-1]
    old = next((a for a in last.get("assignments") or [] if not a.get("warm_up")), {})
    steps |= follow_through(args, c, first, last, old, out)
    other = Client(args.api, args.origin, ctx)
    sign_in_as(other, args.mailpit, f"goal04-{uuid.uuid4().hex[:12]}@example.com")
    codes = [other.request("GET", "/me/plan").status, done(other, first).status]
    codes.append(swap(other, old).status)
    steps["other_account"] = step([] if codes == [404] * 3 else [f"other account codes {codes}"])
    other.close()
    c.close()
    return steps


def done(c: Client, session: dict, key: str | None = None) -> Any:
    headers = {"Idempotency-Key": key or uuid.uuid4().hex}
    return c.request(
        "POST", f"/me/plan/sessions/{session.get('id')}/done", json_body={}, headers=headers
    )


def swap(c: Client, assignment: dict) -> Any:
    return c.request("POST", f"/me/plan/assignments/{assignment.get('id')}/swap", json_body={})


def follow_through(
    args: argparse.Namespace, c: Client, first: dict, last: dict, old: dict, out: dict
) -> dict:
    """Steps 8-9: done twice with one key (timed until GET shows it), then "Not for me"."""
    key, t0, visible = uuid.uuid4().hex, time.perf_counter(), None
    replies = [done(c, first, key)]
    while visible is None and time.perf_counter() - t0 < args.result_timeout:
        now = c.request("GET", "/me/plan").json() or {}
        if any(x.get("id") == first["id"] and x.get("done") for x in now.get("sessions") or []):
            visible = (time.perf_counter() - t0) * 1000
        time.sleep(0.02)
    out["done_visible_ms"] += [visible] if visible is not None else []
    replies.append(done(c, first, key))
    b1, b2 = (d.json() if d.status == 200 else {} for d in replies)
    ok = b1.get("done") is True and b1.get("replayed") is False and b2.get("replayed") is True
    ok = ok and visible is not None and b2.get("plan_version") == b1.get("plan_version")
    steps = {"done": step([] if ok else [f"done {[d.status for d in replies]} {b1} {b2}"])}

    r = swap(c, old)
    sess = (r.json() or {}).get("session", r.json()) if r.status == 200 else {}
    items = sess.get("assignments") or []
    new = next((a for a in items if a.get("id") == old.get("id")), {})
    metric = (old.get("citation") or {}).get("metric_id")
    ok = new.get("drill", {}).get("id") not in (None, old.get("drill", {}).get("id"))
    ok = ok and (new.get("citation") or {}).get("metric_id") == metric
    ok = ok and sum(a.get("minutes") or 0 for a in items) <= last.get("minutes_budget", 0)
    steps["swap"] = step(
        [] if ok else [f"swap {r.status}: {old.get('drill')} -> {new.get('drill')}"]
    )
    return steps


def load(args: argparse.Namespace, ctx: Any) -> dict[str, Any]:
    """G04-02 (c): GET /me/plan on a fixed clock (open loop), one seeded account."""
    steps: dict[str, Any] = {}
    c, match_id, _ = seed(args, ctx, steps)
    gen = c.request("POST", "/me/plan", json_body=PREFS).status if match_id else None
    if gen != 201:
        return {"ok": False, "seed": steps, "generate_status": gen}
    local, lock, lat, codes = threading.local(), threading.Lock(), [], []

    def fire(due: float) -> None:
        time.sleep(max(0.0, due - time.perf_counter()))
        if not hasattr(local, "c"):
            local.c = Client(args.api, args.origin, ctx, timeout=10)
            local.c.cookie = c.cookie
        try:
            r = local.c.request("GET", "/me/plan")
            status, ms = r.status, r.ms
        except (OSError, http.client.HTTPException):
            status, ms = 0, None
        with lock:
            codes.append(status)
            lat.extend([ms] if ms is not None and status == 200 else [])

    start = time.perf_counter() + 0.5
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i in range(int(args.rps * args.duration)):
            pool.submit(fire, start + i / args.rps)
    summary = latency_summary(lat, codes, time.perf_counter() - start)
    summary["ok"] = bool(
        summary["p95_ms"] is not None
        and summary["p95_ms"] <= args.max_load_p95_ms
        and summary["p99_ms"] <= args.max_load_p99_ms
        and summary["availability"] >= 0.995
        and summary["status_unexpected"] == 0
        and summary["achieved_rps"] >= 0.95 * args.rps
    )
    return summary | {"target_rps": args.rps, "duration_s": args.duration}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base-url", default="https://localhost:3000")
    p.add_argument("--mailpit", default="http://127.0.0.1:8025")
    p.add_argument("--cacert")
    p.add_argument("--insecure-loopback", action="store_true")
    p.add_argument("--file", default="fixtures/clips/synthetic-60s/clip.mp4")
    p.add_argument("--drills", type=Path, default=REPO / "content" / "drills")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--generations", type=int, default=4)
    p.add_argument("--determinism", type=int, default=0)
    p.add_argument("--load", action="store_true")
    p.add_argument("--rps", type=float, default=50.0)
    p.add_argument("--duration", type=float, default=60.0)
    p.add_argument("--workers", type=int, default=64)
    p.add_argument("--max-generate-p95-ms", type=float, default=5000.0)
    p.add_argument("--max-done-p95-ms", type=float, default=1000.0)
    p.add_argument("--max-load-p95-ms", type=float, default=300.0)
    p.add_argument("--max-load-p99-ms", type=float, default=800.0)
    p.add_argument("--result-timeout", type=float, default=30.0)
    p.add_argument("--json", type=Path)
    p.add_argument("--min-free-gb", type=int, default=10)
    args = p.parse_args(argv)
    args.origin = args.base_url.rstrip("/")
    args.api = args.origin + "/api"

    free_gb = shutil.disk_usage("/").free // 1024**3
    if free_gb < args.min_free_gb:
        print(
            f"live_plan: only {free_gb} GB free on /, need >= {args.min_free_gb} GB",
            file=sys.stderr,
        )
        return 2
    ctx = ssl_context(args.cacert, args.insecure_loopback)
    try:
        args.data, library = Path(args.file).read_bytes(), pl.load_library(args.drills)
        probe = Client(args.api, args.origin, ctx, timeout=10).request("GET", "/config/public")
        if probe.status != 200 or not library:
            raise OSError(f"GET /config/public {probe.status}, {len(library)} drills")
    except (OSError, ValueError, KeyError, http.client.HTTPException) as exc:
        print(f"live_plan: cannot read the stack or its inputs: {exc}", file=sys.stderr)
        return 2

    if args.load:
        summary, runs = load(args, ctx), []
    else:
        out: dict[str, list[float]] = {"generate_ms": [], "done_visible_ms": []}
        runs = [run(args, ctx, library, out) for _ in range(args.runs)]
        passed = sum(len(r) == 11 and all(x["ok"] for x in r.values()) for r in runs)
        summary = {
            "runs": args.runs,
            "runs_passed": passed,
            "generate": t.timing_summary(
                out["generate_ms"],
                max_p95_ms=args.max_generate_p95_ms,
                min_n=args.runs * args.generations,
            ),
            "done_visible": t.timing_summary(
                out["done_visible_ms"], max_p95_ms=args.max_done_p95_ms, min_n=args.runs
            ),
            "reference": pl.reference_check(REPO),
        }
        summary["ok"] = bool(args.runs > 0 and passed == args.runs) and all(
            summary[x]["ok"] for x in ("generate", "done_visible", "reference")
        )
    print(json.dumps(summary, indent=2, default=str))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps({"summary": summary, "runs": runs}, indent=2, default=str) + "\n"
        )
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
