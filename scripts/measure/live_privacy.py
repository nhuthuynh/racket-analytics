#!/usr/bin/env python3
"""Live privacy and quota harness (goal scorecard G04-09, G04-10; QA-HARNESS-4b).

Routes and codes: docs/architecture/api-sprint-04.md §4-§7 (PE-4). Fresh accounts every run.
--flags off: every Sprint 4 privacy route answers 404, /config/public has every feature off,
  GET /me and the match carry no field the flags add (G04-09 a).
--flags on, per run: (b) an under-18 answer is 403 `under_age` with a reason, 0 new rows in
  `accounts` (--psql), the session ends; an adult is confirmed and usable. On the adult's
  uploaded, tagged match with a plan: (d) the match is absent from a built label set
  (--label-set-cmd) until opt-in, present after it, absent after revoke; (c) retention 30 days,
  `review_video_delete_at` shown, purge (--purge-cmd, e.g. `... purge --once
  --now-offset-days 31`) -> the review video link 404, stats, score sheet and plan 200.
--quotas (once): (a) a burst of 50 POST /matches -> exactly 10 accepted, the rest 429
  `rate_limited` with `retry_at` (flags off: all 50 accepted); (b) uploads declared up to the
  storage quota, then one more -> 429 `storage_quota_exceeded` naming usage and limit, no
  Location, stored bytes (--stored-bytes-cmd) unchanged; flags on also runs the alert-rule test
  (--alert-test-cmd prints SUCCESS) and counts the billing rules in --alert-rules (6).
Exit 0 only when every step passed, 1 when one failed, 2 when it refuses to start.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import statslib as s
import tagcontract as k
from live_goal import create_upload, new_match
from live_tagging import Session, _fetch, upload_video
from livehttp import Client, sign_in, ssl_context

BURST, PER_HOUR, BILLING_RULES = 50, 10, 6
Stored = tuple[int | None, int | None]  # object-store bytes before and after a refusal
FLAG_ROUTES = (("GET", "/me/retention"), ("GET", "/me/training-consent"), ("GET", "/me/quota"))
PLAN_BODY = {"minutes_per_session": 60, "sessions_per_week": 2, "players_available": 4,
             "equipment": ["full_court"], "level": "intermediate"}  # fmt: skip


def first_int(text: str) -> int | None:
    found = re.search(r"\d+", text)
    return int(found.group()) if found else None


def command(cmd: str, timeout: float = 600) -> tuple[int, str]:
    done = subprocess.run(  # noqa: S603 (operator-supplied local command, no shell)
        shlex.split(cmd), capture_output=True, text=True, timeout=timeout, check=False
    )
    return done.returncode, done.stdout + done.stderr


def psql(cmd: str, sql: str) -> str:
    rc, out = command(f"{cmd} -At -c {shlex.quote(sql)}", 120)
    if rc != 0:
        raise RuntimeError(f"psql rc={rc}: {out.strip()[:200]}")
    return out


def burst_problems(replies: list[tuple[int, Any]], *, flags_on: bool) -> list[str]:
    want = PER_HOUR if flags_on else BURST
    accepted = [i for i, (st, _) in enumerate(replies) if st == 201]
    problems = [] if len(accepted) == want else [f"{len(accepted)} accepted, want {want}"]
    refused = [i for i, (st, _) in enumerate(replies) if st != 201]
    if refused and accepted and accepted[-1] > refused[0]:
        problems.append(f"request {accepted[-1] + 1} accepted after a refusal")
    for st, body in (replies[i] for i in refused):
        if st != 429 or (body or {}).get("code") != "rate_limited":
            problems.append(f"status {st} {(body or {}).get('code')}")
        elif not body.get("retry_at"):
            problems.append("429 without retry_at")
    return problems[:10]


def quota_problems(
    status: int, body: Any, location: str | None, stored: Stored, *, flags_on: bool
) -> list[str]:
    body = body if isinstance(body, dict) else {}
    if not flags_on:  # only an accepted upload session counts (ADR 0014: no vacuous pass)
        refused = body.get("code") == "storage_quota_exceeded" or "quota" in body
        problems = ["refused by the quota with the flag off"] if refused else []
        sessions_cap = status == 429 and body.get("code") == "upload_quota_exceeded"
        if (status != 201 or not location) and not sessions_cap:  # api-sprint-01 §6.3 check 5
            problems.append(f"status {status}, Location {location!r} with the flag off")
        return problems
    if status != 429 or location:
        return [f"status {status}, Location {location!r}"]
    problems = [] if body.get("code") == "storage_quota_exceeded" else [f"code {body.get('code')}"]
    if not {"used_bytes", "limit_bytes"} <= set(body.get("quota") or {}):
        problems.append("body lacks quota usage and limit")
    if None in stored:
        problems.append("stored bytes unreadable")
    elif stored[0] != stored[1]:
        problems.append(f"stored bytes changed: {stored[0]} -> {stored[1]}")
    return problems


def fill_sizes(limit: int, used: int, max_bytes: int) -> list[int]:
    if limit < 0 or (limit > used and max_bytes <= 0):
        raise ValueError(f"cannot fill limit {limit} with uploads of {max_bytes}")
    left, sizes = limit - used, []
    while left > 0:
        sizes.append(min(left, max_bytes))
        left -= sizes[-1]
    return sizes


def alert_problems(rc: int, out: str, rules: int) -> list[str]:
    problems = [] if rc == 0 else [f"alert test rc={rc}"]
    problems += [] if "SUCCESS" in out else ["alert test printed no SUCCESS"]
    if rules != BILLING_RULES:
        problems.append(f"{rules} billing alert rules, want {BILLING_RULES}")
    return problems


def verdict(out: dict[str, Any]) -> bool:
    """True only when at least one step ran and every step reports ok True."""
    steps = [st for run in out.get("runs", []) for st in run.values()]
    steps += list(out.get("quotas", {}).values())
    return bool(steps) and all(st.get("ok") is True for st in steps)


def _step(problems: list[str], **facts: Any) -> dict[str, Any]:
    return {"ok": not problems, "problems": problems, **facts}


def _client(args: argparse.Namespace) -> Client:
    return Client(args.api, args.origin, ssl_context(args.cacert, args.insecure_loopback))


def _match(c: Client) -> str:
    match_id = new_match(c)
    if not match_id:
        raise RuntimeError("match creation failed")
    return match_id


def _account(args: argparse.Namespace) -> Client:
    c = _client(args)
    if not sign_in(c, args.mailpit)["ok"]:
        raise RuntimeError("sign-in failed")
    if args.flags == "on":
        r = c.request("POST", "/me/age-confirmation", json_body={"is_adult": True})
        if r.status != 200 or not r.json().get("age_confirmed_at"):
            raise RuntimeError(f"adult age confirmation status {r.status}")
    return c


def age_step(args: argparse.Namespace) -> tuple[dict[str, Any], Client | None]:
    try:
        before = first_int(psql(args.psql, "SELECT count(*) FROM accounts"))
        minor = _client(args)
        signed = sign_in(minor, args.mailpit)["ok"]
        r = minor.request("POST", "/me/age-confirmation", json_body={"is_adult": False})
        body, after_me = r.json() or {}, minor.request("GET", "/me").status
        new_rows = (first_int(psql(args.psql, "SELECT count(*) FROM accounts")) or 0) - (
            before or 0
        )
        problems = [] if signed else ["under-18 sign-in failed"]
        if r.status != 403 or body.get("code") != "under_age" or not body.get("message"):
            problems.append(f"under-18 answer status {r.status} {body.get('code')}")
        problems += [f"{new_rows} new account rows"] if new_rows or before is None else []
        problems += [] if after_me == 401 else [f"GET /me after refusal {after_me}"]
        adult = _account(args)
        if (me := adult.request("GET", "/me").status) != 200:
            problems.append(f"adult GET /me {me}")
        return _step(problems, new_rows=new_rows), adult
    except (RuntimeError, OSError, ValueError) as exc:
        return _step([str(exc)]), None


def prepare(c: Client, args: argparse.Namespace, data: bytes) -> str:
    match_id = new_match(c)
    if not match_id or not upload_video(c, match_id, data, args.result_timeout)["ok"]:
        raise RuntimeError(f"match or upload failed for {match_id}")
    sess = Session(c, match_id)
    codes = [sess.call("start_game", k.START_GAME_BODY).status]
    codes += [sess.call("tag", tag).status for tag in s.STATS_TAGS]
    codes.append(c.request("POST", "/me/plan", json_body=PLAN_BODY).status)
    if any(code not in (200, 201) for code in codes):
        raise RuntimeError(f"tagging or plan statuses {sorted(set(codes))}")
    return match_id


def consent_step(c: Client, args: argparse.Namespace, match_id: str) -> dict[str, Any]:
    problems, seen = [], []
    first = c.request("GET", "/me/training-consent")
    if first.status != 200 or first.json().get("opt_in") is not False:
        problems.append(f"consent not off by default: {first.status}")
    for opt_in, when in ((None, "before opt-in"), (True, "after opt-in"), (False, "after revoke")):
        if opt_in is not None:
            r = c.request("PUT", "/me/training-consent", json_body={"opt_in": opt_in})
            problems += [] if r.status == 200 else [f"PUT consent {opt_in}: {r.status}"]
        rc, out = command(args.label_set_cmd)
        seen.append(match_id in out)
        if rc != 0:
            problems.append(f"label-set rc={rc} {when}")
        elif (match_id in out) != bool(opt_in):
            problems.append(
                f"match {'in' if match_id in out else 'missing from'} the label set {when}"
            )
    return _step(problems, in_label_set=seen)


def retention_step(c: Client, args: argparse.Namespace, match_id: str) -> dict[str, Any]:
    ctx = ssl_context(args.cacert, args.insecure_loopback)
    put = c.request("PUT", "/me/retention", json_body={"review_video_days": 30})
    problems = [] if put.status == 200 else [f"PUT retention {put.status}"]
    if not (c.request("GET", f"/matches/{match_id}").json() or {}).get("review_video_delete_at"):
        problems.append("review_video_delete_at not shown")
    link = c.request(*k.path("video", match_id=match_id))
    url = (link.json() or {}).get(k.MEDIA_URL) or "" if link.status == 200 else ""
    if (before := _fetch(url, ctx, {"Range": "bytes=0-1"})) != 206:
        problems.append(f"review video status {before} before purge")
    rc, out = command(args.purge_cmd)
    problems += [] if rc == 0 else [f"purge rc={rc}: {out.strip()[:200]}"]
    if (after := _fetch(url, ctx, {"Range": "bytes=0-1"})) != 404:
        problems.append(f"review video status {after} after purge")
    for p in (f"/matches/{match_id}/stats", f"/matches/{match_id}/score-sheet", "/me/plan"):
        if (st := c.request("GET", p).status) != 200:
            problems.append(f"GET {p} {st} after purge")
    return _step(problems)


def burst_step(args: argparse.Namespace) -> dict[str, Any]:
    try:
        c = _account(args)
        body = {"format": "singles", "scoring_system": "side_out",
                "played_on": dt.date.today().isoformat()}  # fmt: skip
        replies = [c.request("POST", "/matches", json_body=body) for _ in range(BURST)]
        seen = [(r.status, r.json()) for r in replies]
        return _step(
            burst_problems(seen, flags_on=args.flags == "on"), statuses=[x for x, _ in seen]
        )
    except (RuntimeError, OSError, ValueError) as exc:
        return _step([str(exc)])


def _stored(args: argparse.Namespace) -> int | None:
    if args.flags != "on":
        return None
    rc, out = command(args.stored_bytes_cmd, 120)
    return first_int(out) if rc == 0 else None


def quota_step(args: argparse.Namespace) -> dict[str, Any]:
    try:
        c = _account(args)
        q = c.request("GET", "/me/quota")
        storage = (q.json() or {}).get("storage", {}) if q.status == 200 else {}
        limit, used = storage.get("limit_bytes") or args.quota_bytes, storage.get("used_bytes", 0)
        max_bytes = c.request("GET", "/upload-policy").json()["max_bytes"]
        for n in fill_sizes(limit, used, max_bytes):
            st, _ = create_upload(c, _match(c), n, "fill.mp4")
            if st != 201:
                return _step([f"fill upload of {n} bytes: status {st}"])
        before, over = _stored(args), _match(c)
        r = c.request("POST", f"/matches/{over}/uploads", headers={
            "Tus-Resumable": "1.0.0", "Upload-Length": str(1 << 20)})  # fmt: skip
        stored = (before, _stored(args))
        problems = quota_problems(r.status, r.json(), r.headers.get("Location"), stored,
                                  flags_on=args.flags == "on")  # fmt: skip
        return _step(problems, status=r.status, stored_bytes=stored)
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        return _step([str(exc)])


def alerts_step(args: argparse.Namespace) -> dict[str, Any]:
    try:
        rc, text = command(args.alert_test_cmd)
        rules = len(re.findall(r"^\s*- alert:", Path(args.alert_rules).read_text(), re.M))
        return _step(alert_problems(rc, text, rules), rules=rules)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return _step([str(exc)])


def quota_steps(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    """G04-10, once per invocation: burst and quota; flags on adds the alert-rule test."""
    steps = {"burst": burst_step(args), "quota": quota_step(args)}
    if args.flags == "on":
        steps["alerts"] = alerts_step(args)
    return steps


def flags_off_step(args: argparse.Namespace) -> dict[str, Any]:
    try:
        c = _account(args)
        features = (c.request("GET", "/config/public").json() or {}).get("features") or {}
        problems = [f"feature on: {f}" for f, on in features.items() if on]
        problems += [] if features else ["/config/public lists no features"]
        codes = [c.request(m, p).status for m, p in FLAG_ROUTES]
        codes.append(c.request("POST", "/me/age-confirmation", json_body={"is_adult": True}).status)
        problems += [f"flag route answered {x}" for x in codes if x != 404]
        for key, path in (("age_confirmed_at", "/me"),
                          ("review_video_delete_at", f"/matches/{_match(c)}")):  # fmt: skip
            r = c.request("GET", path)
            body = r.json() if r.status == 200 else None
            if not isinstance(body, dict):
                problems.append(f"GET {path} status {r.status}")
            elif key in body:
                problems.append(f"{key} served with the flag off")
        return _step(problems, codes=codes)
    except (RuntimeError, OSError, ValueError) as exc:
        return _step([str(exc)])


def one_run(args: argparse.Namespace, data: bytes) -> dict[str, Any]:
    if args.flags == "off":
        return {"flags_off": flags_off_step(args)}
    age, adult = age_step(args)
    steps = {"age": age}
    try:
        match_id = prepare(adult, args, data) if adult else None
    except (RuntimeError, OSError, ValueError) as exc:
        steps["prepare"], match_id = _step([str(exc)]), None
    if adult and match_id:
        steps["consent"] = consent_step(adult, args, match_id)
        steps["retention"] = retention_step(adult, args, match_id)
    else:
        steps["consent"] = steps["retention"] = _step(["no adult account with a prepared match"])
    return steps


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--flags", choices=("on", "off"), required=True)
    p.add_argument("--api", default="https://localhost:3000/api")
    p.add_argument("--origin", default="https://localhost:3000")
    p.add_argument("--mailpit", default="http://127.0.0.1:8025")
    p.add_argument("--cacert")
    p.add_argument("--insecure-loopback", action="store_true")
    p.add_argument("--file", default="fixtures/clips/synthetic-60s/clip.mp4")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--result-timeout", type=float, default=120.0)
    for opt in ("--psql", "--purge-cmd", "--label-set-cmd", "--stored-bytes-cmd",
                "--alert-test-cmd", "--alert-rules"):  # fmt: skip
        p.add_argument(opt)
    p.add_argument("--quotas", action="store_true")
    p.add_argument("--quota-bytes", type=int, default=21_474_836_480, help="flags off only")
    p.add_argument("--json", type=Path)
    p.add_argument("--min-free-gb", type=int, default=10)
    args = p.parse_args(argv)
    need = ["psql", "purge_cmd", "label_set_cmd"] if args.flags == "on" else []
    need += ["stored_bytes_cmd", "alert_test_cmd", "alert_rules"] if args.quotas and need else []
    missing = [f"--{n.replace('_', '-')}" for n in need if not getattr(args, n)]
    if missing or args.runs < 1:
        print(f"live_privacy: missing {' '.join(missing) or '--runs >= 1'}", file=sys.stderr)
        return 2
    if (free := shutil.disk_usage("/").free // 1024**3) < args.min_free_gb:
        print(
            f"live_privacy: only {free} GB free on /, need >= {args.min_free_gb}", file=sys.stderr
        )
        return 2
    data = Path(args.file).read_bytes() if args.flags == "on" else b""
    out: dict[str, Any] = {
        "flags": args.flags,
        "runs": [one_run(args, data) for _ in range(args.runs)],
    }
    if args.quotas:
        out["quotas"] = quota_steps(args)
    out["ok"] = verdict(out)
    text = json.dumps(out, indent=2, default=str)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
