#!/usr/bin/env python3
"""Live Sprint 3 goal journey: starter stats, evidence, deletion and purge (G03-01..G03-03).

Each run is a fresh account on the live stack over https (ADR 0029):

 1. magic-link sign-in; a doubles match; the fixture uploaded; "Video received";
 2. the coach's worked example tagged rally by rally (statslib.STATS_TAGS); after each tag the
    stats are polled until they equal the reference for the rallies so far (NFR-017 analogue,
    "tag -> stats current");
 3. stats = reference for AN-01..AN-07 x 2 sides (values, n, Wilson bounds, low-sample flags),
    with `rules_version`, `metric_def_version` and the "unofficial" label;
 4. "Show me" for every metric and side with n > 0: <= 10 rallies, total = n, each rally behind
    the metric (FR-103, NFR-038); the first item's rally video answers a Range request with 206;
 5. rally 3 corrected -> stats recomputed to the corrected reference (timed);
 6. a second account gets 404 on stats and evidence (NFR-051);
 7. DELETE the match -> 404 on the match and its stats and gone from the list (timed, <= 60 s,
    NFR-066 a);
 8. DELETE the account -> the old session gets 401; signing in again with the same address
    gives an empty account under a new id (FR-007).

With ``--psql`` and ``--purge-cmd`` it then runs the purge job once and checks that no row in
any public table holds a deleted match or account id (the ids recorded at setup; a run whose
GET /me names no account id fails setup), and that the rally video links taken in
step 4 (still within their TTL) now answer 404 (NFR-066 b).

    python3 scripts/measure/live_stats.py --api https://localhost:33000/api \
        --origin https://localhost:33000 --mailpit http://127.0.0.1:38025 \
        --cacert .local/goal03/root.crt --runs 5 \
        --psql "$DC exec -T postgres psql -U racket -d racket -At -F|" \
        --purge-cmd "$DC exec -T worker python -m racket.platform.purge --once" \
        --json reports/goal03/live-stats.json

Exit 0 only when every step of every run passed, the timings met their targets and the purge
check (when asked) found nothing left; 2 when it refuses to start (disk floor). Routes and
fields: statscontract.py (assumptions until api-sprint-03.md exists) and tagcontract.py.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import statscontract as sk
import statslib as s
import tagcontract as k
import taglib as t
from live_goal import new_match
from live_tagging import Session, _code, _fetch, upload_video
from livehttp import Client, mailpit_token, ssl_context


def sign_in_as(c: Client, mailpit: str, address: str) -> bool:
    link = c.request("POST", "/auth/links", json_body={"email": address})
    token = mailpit_token(mailpit, address) if link.status == 202 else None
    if not token:
        return False
    r = c.request("POST", "/auth/exchange", json_body={"token": token})
    return r.status == 200 and bool(c.cookie)


def _get(c: Client, name: str, **ids: str) -> Any:
    return c.request(*sk.path(name, **ids))


def _poll_stats(
    c: Client, match_id: str, expected: dict[str, Any], timeout_s: float
) -> tuple[float | None, list[str]]:
    """ms until the stats equal ``expected``, or None with the last differences."""
    t0, diffs = time.perf_counter(), ["never fetched"]
    while time.perf_counter() - t0 < timeout_s:
        r = _get(c, "stats", match_id=match_id)
        diffs = s.compare_stats(expected, r.json()) if r.status == 200 else [f"status {r.status}"]
        if not diffs:
            return (time.perf_counter() - t0) * 1000, []
        time.sleep(0.05)
    return None, diffs


def _reference(tags: list[dict[str, Any]]) -> dict[str, Any]:
    return s.starter_stats([{"first_serving_side": "A", "tags": tags}])


def account_id(me: Any) -> str | None:
    """The account id in a GET /me body, or None when there is none to read."""
    value = me.get("id") if isinstance(me, dict) else None
    return value if isinstance(value, str) and value else None


def record_run_ids(out: dict[str, Any], match_id: str, me: Any) -> list[str]:
    """Record the match and account this run will delete; refuse when /me names no account.

    The purge check (G03-03) inventories exactly these ids, so an id the harness cannot read
    is a failed setup, never a silent gap in the inventory (PE-1).
    """
    acc = account_id(me)
    if acc is None:
        return [f"GET /me returned no account id: {me!r}"[:200]]
    out["deleted_ids"] += [match_id, acc]
    return []


def judge_account_deletion(
    *,
    deleted_id: str | None,
    status: int,
    old_session: int,
    back: bool,
    items: Any,
    again_me: Any,
) -> dict[str, Any]:
    """G03-01 step 8: the account went away and signing in again gives a new, empty account."""
    again_id = account_id(again_me) if back else None
    problems = []
    if status not in sk.DELETE_OK:
        problems.append(f"DELETE /me status {status}")
    if old_session != 401:
        problems.append(f"old session status {old_session}")
    if not back:
        problems.append("could not sign in again with the same address")
    elif items != []:
        problems.append(f"matches after signing in again: {items!r}"[:200])
    if not deleted_id:
        problems.append("no deleted account id recorded")
    if back and again_id is None:
        problems.append("GET /me after signing in again returned no account id")
    elif again_id is not None and again_id == deleted_id:
        problems.append(f"signed in again under the deleted account id {deleted_id}")
    return {
        "ok": not problems,
        "problems": problems,
        "status": status,
        "old_session": old_session,
        "items_after_sign_in": items,
        "deleted_id": deleted_id,
        "again_id": again_id,
    }


def run(args: argparse.Namespace, data: bytes, ctx: Any, out: dict[str, Any]) -> dict[str, Any]:
    steps: dict[str, Any] = {}
    c = Client(args.api, args.origin, ctx)
    address = f"goal03-{uuid.uuid4().hex[:12]}@example.com"
    ok = sign_in_as(c, args.mailpit, address)
    match_id = new_match(c) if ok else None
    video = upload_video(c, match_id, data, args.result_timeout) if match_id else {"ok": False}
    steps["setup"] = {"ok": bool(ok and match_id and video.get("ok")), "video": video}
    if not steps["setup"]["ok"]:
        return steps
    me = _get(c, "me").json()
    problems = record_run_ids(out, match_id, me)
    if problems:
        steps["setup"] = {"ok": False, "video": video, "problems": problems}
        return steps
    deleted_account = account_id(me)

    # 2. tag -> stats current, rally by rally
    sess = Session(c, match_id)
    started = sess.call("start_game", {**k.START_GAME_BODY, "first_serving_side": "A"})
    ids, current, diffs = [], [], []
    for i, tag in enumerate(s.STATS_TAGS):
        r = sess.call("tag", tag)
        if r.status != 201:
            diffs.append(f"rally {i + 1}: status {r.status} {_code(r)}")
            break
        ids.append(r.json().get(k.RALLY_ID_KEY))
        ms, d = _poll_stats(c, match_id, _reference(s.STATS_TAGS[: i + 1]), args.result_timeout)
        if ms is None:
            diffs += [f"after rally {i + 1}: {x}" for x in d[:5]]
        else:
            current.append(ms)
    out["stats_current_ms"] += current
    steps["tag_to_stats"] = {"ok": started.status in (200, 201) and not diffs, "diffs": diffs[:20]}

    # 3. stats equal the reference, versions and label present
    expected = _reference(s.STATS_TAGS)
    body = _get(c, "stats", match_id=match_id).json() or {}
    problems = s.compare_stats(expected, body)
    for key in (sk.RULES_VERSION_KEY, sk.DEF_VERSION_KEY):
        if not body.get(key):
            problems.append(f"{key} missing")
    if body.get("label") != t.UNOFFICIAL_LABEL or body.get("unofficial") is not True:
        problems.append(f"unofficial label missing: {body.get('label')!r}")
    steps["stats"] = {"ok": not problems, "diffs": problems[:20]}

    # 4. evidence behind every metric and side; the first item plays (Range 206)
    ev_problems, played = [], None
    for metric in s.METRICS:
        for side in t.SIDES:
            refs = expected[metric][side]["rallies"]
            if not refs:
                continue
            r = _get(c, "evidence", match_id=match_id, metric_id=metric, side=side)
            ev = r.json() if r.status == 200 else {}
            ev_problems += [f"{metric} {side}: {p}" for p in s.evidence_problems(ev, refs)]
            items = ev.get(sk.EVIDENCE_ITEMS) or []
            if played is None and items:
                rid = items[0].get(sk.EVIDENCE_RALLY_ID) or ""
                m = c.request(*k.path("media", match_id=match_id, rally_id=rid))
                link = m.json() if m.status == 200 else {}
                url = link.get(k.MEDIA_URL) or ""
                played = _fetch(url, ctx, {"Range": "bytes=0-1023"}) if url else None
                ttl = float(link.get(k.MEDIA_TTL) or 0)
                out["media"].append({"url": url, "valid_until": time.time() + ttl})
    if played != 206:
        ev_problems.append(f"evidence rally video Range status {played}")
    steps["evidence"] = {"ok": not ev_problems, "problems": ev_problems[:20]}

    # 5. a correction recomputes the stats
    corrected = t.with_winner(s.STATS_TAGS, rally=s.CORRECTED_RALLY, side="A")
    r = sess.call(
        "correct",
        {"field": "winning_side", "value": "A"},
        rally_id=ids[s.CORRECTED_RALLY - 1] if len(ids) >= s.CORRECTED_RALLY else "",
    )
    ms, d = _poll_stats(c, match_id, _reference(corrected), args.result_timeout)
    if ms is not None:
        out["correction_to_stats_ms"].append(ms)
    steps["correction"] = {"ok": r.status == 200 and ms is not None, "diffs": d[:10]}

    # 6. another account sees nothing
    other = Client(args.api, args.origin, ctx)
    other_ok = sign_in_as(other, args.mailpit, f"goal03-{uuid.uuid4().hex[:12]}@example.com")
    codes = [
        _get(other, "stats", match_id=match_id).status,
        _get(other, "evidence", match_id=match_id, metric_id="AN-01", side="A").status,
    ]
    steps["other_account"] = {"ok": other_ok and codes == [404, 404], "codes": codes}
    other.close()

    # 7. delete the match: hidden within 60 s
    r = c.request(*sk.path("delete_match", match_id=match_id), json_body=sk.CONFIRM_BODY)
    t0, hidden_ms = time.perf_counter(), None
    while r.status in sk.DELETE_OK and time.perf_counter() - t0 < args.hidden_timeout:
        listed = _get(c, "matches").json() or {}
        in_list = any(m.get("id") == match_id for m in listed.get("items", []))
        if _get(c, "match", match_id=match_id).status == 404 and not in_list:
            hidden_ms = (time.perf_counter() - t0) * 1000
            break
        time.sleep(0.1)
    stats_after = _get(c, "stats", match_id=match_id).status
    if hidden_ms is not None:
        out["hidden_ms"].append(hidden_ms)
    steps["delete_match"] = {
        "ok": hidden_ms is not None and stats_after == 404,
        "status": r.status,
        "stats_after": stats_after,
    }

    # 8. delete the account: signed out, the address starts again empty
    old_cookie = c.cookie
    r = c.request(*sk.path("delete_account"), json_body=sk.CONFIRM_BODY)
    probe = Client(args.api, args.origin, ctx)
    probe.cookie = old_cookie
    old_session = _get(probe, "matches").status
    probe.close()
    again = Client(args.api, args.origin, ctx)
    back = sign_in_as(again, args.mailpit, address)
    items = (_get(again, "matches").json() or {}).get("items") if back else None
    again_me = _get(again, "me").json() if back else None
    steps["delete_account"] = judge_account_deletion(
        deleted_id=deleted_account,
        status=r.status,
        old_session=old_session,
        back=back,
        items=items,
        again_me=again_me,
    )
    again.close()
    c.close()
    return steps


def _psql(cmd: str, sql: str) -> str:
    done = subprocess.run(  # noqa: S603 (operator-supplied local command, no shell)
        [*shlex.split(cmd), "-c", sql], capture_output=True, text=True, timeout=120, check=False
    )
    if done.returncode != 0:
        raise RuntimeError(f"psql rc={done.returncode}: {done.stderr.strip()[:200]}")
    return done.stdout


def purge_check(args: argparse.Namespace, ctx: Any, out: dict[str, Any]) -> dict[str, Any]:
    done = subprocess.run(  # noqa: S603 (operator-supplied local command, no shell)
        shlex.split(args.purge_cmd), capture_output=True, text=True, timeout=600, check=False
    )
    ids = list(out["deleted_ids"])  # recorded at setup; never inferred by subtraction (PE-1)
    try:
        pairs = s.parse_pairs(_psql(args.psql, s.columns_sql())) + list(s.ROOT_TABLES)
        counts = s.parse_counts(_psql(args.psql, s.count_sql(pairs, ids))) if ids else {}
        problems = s.purge_problems(counts)
    except (RuntimeError, ValueError) as exc:
        counts, problems = {}, [str(exc)]
    if not ids:
        problems.insert(0, "no deleted id to check")
    media, checked = [], 0
    for m in out["media"]:
        if not m["url"] or time.time() >= m["valid_until"] - 5:
            media.append("unchecked (link expired)")
            continue
        status = _fetch(m["url"], ctx, {"Range": "bytes=0-1"})
        checked += 1
        media.append(status)
        if status != 404:
            problems.append(f"media object still served after purge: status {status}")
    if checked == 0:
        problems.append("no media link checked within its TTL")
    if done.returncode != 0:
        problems.append(f"purge command rc={done.returncode}")
    return {
        "ok": not problems,
        "ids": ids,
        "rows": counts,
        "media": media,
        "problems": problems[:20],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--api", default="https://localhost:3000/api")
    p.add_argument("--origin", default="https://localhost:3000")
    p.add_argument("--mailpit", default="http://127.0.0.1:8025")
    p.add_argument("--cacert")
    p.add_argument("--insecure-loopback", action="store_true")
    p.add_argument("--file", default="fixtures/clips/synthetic-60s/clip.mp4")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--max-stats-current-p95-ms", type=float, default=5000.0)
    p.add_argument("--max-hidden-p95-ms", type=float, default=60_000.0)
    p.add_argument("--hidden-timeout", type=float, default=90.0)
    p.add_argument("--result-timeout", type=float, default=30.0)
    p.add_argument("--psql", help="command that runs psql -At -F'|' against the stack's DB")
    p.add_argument("--purge-cmd", help="command that runs the purge job once")
    p.add_argument("--json", type=Path)
    p.add_argument("--min-free-gb", type=int, default=10)
    args = p.parse_args(argv)

    free_gb = shutil.disk_usage("/").free // 1024**3
    if free_gb < args.min_free_gb:
        print(
            f"live_stats: only {free_gb} GB free on /, need >= {args.min_free_gb} GB; "
            "prune first (bash scripts/disk-precheck.sh, docs/ops/disk-and-prune.md)",
            file=sys.stderr,
        )
        return 2
    if bool(args.psql) != bool(args.purge_cmd):
        print("live_stats: --psql and --purge-cmd go together", file=sys.stderr)
        return 2

    ctx = ssl_context(args.cacert, args.insecure_loopback)
    data = Path(args.file).read_bytes()
    out: dict[str, Any] = {
        "deleted_ids": [],
        "media": [],
        "stats_current_ms": [],
        "correction_to_stats_ms": [],
        "hidden_ms": [],
    }
    runs = [run(args, data, ctx, out) for _ in range(args.runs)]
    passed = sum(all(step.get("ok") for step in r.values()) and len(r) > 1 for r in runs)
    current = t.timing_summary(
        out["stats_current_ms"], max_p95_ms=args.max_stats_current_p95_ms, min_n=args.runs
    )
    correction = t.timing_summary(
        out["correction_to_stats_ms"], max_p95_ms=args.max_stats_current_p95_ms, min_n=args.runs
    )
    hidden = t.timing_summary(out["hidden_ms"], max_p95_ms=args.max_hidden_p95_ms, min_n=args.runs)
    purge = purge_check(args, ctx, out) if args.psql else None
    summary = {
        "runs": args.runs,
        "runs_passed": passed,
        "tag_to_stats": current,
        "correction_to_stats": correction,
        "delete_hidden": hidden,
        "purge": purge,
    }
    summary["ok"] = bool(
        args.runs > 0
        and passed == args.runs
        and current["ok"]
        and correction["ok"]
        and hidden["ok"]
        and (purge is None or purge["ok"])
    )
    report = {"summary": summary, "runs": runs}
    text = json.dumps(report, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
