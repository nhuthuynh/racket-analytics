#!/usr/bin/env python3
"""Sprint 2 goal journey, live and in real time (goal scorecard G02-01, G02-02).

Runs the user-visible Sprint 2 goal against a running local stack, through the browser's
origin (default https://localhost:3000/api, ADR 0029), as fresh accounts per run:

  1. magic-link sign-in; a doubles match; the 60 s fixture uploaded by tus; "Video received"
  2. tagging a match with no video is refused (409, NFR-060)
  3. game 1 started; the 6-rally journey tagged one by one (ST-027): every response carries
     the new score, equal to the reference (taglib.expected_rows)
  4. the score sheet equals the expected rows, says "unofficial scoring (rules not yet
     verified)" and carries rules_version (ST-030, FR-049, FR-055, NFR-075)
  5. an error credited to the winning side is refused (422) and the sheet is unchanged
  6. a stale If-Match version is refused (409 stale_match, IT-02-04)
  7. rally 2's winner corrected: rallies 2-6 re-scored as a fresh build (C-01), rally 2
     marked corrected_by_user, the history lists field, old and new value (ST-031, ST-032)
  8. undo: the sheet is byte-identical to the one before the correction (C-04), and the
     history lists the correction and the undo
  9. second match: the 14-rally conflict game; rally 11 corrected so the game ends there;
     rallies 12-14 kept and marked needs_decision (C-02, @needs-verification, ADR 0009)
 10. rally 3's media link: TTL <= 15 min, no session token in the URL, a Range request gets
     206, a tampered signature is refused (ST-037, NFR-055)
 11. a second account gets 404 on the sheet, history and media routes (IT-02-05)
 12. sign-out

With --corrections N it also tags a decided best-of-3 match (taglib.three_game_script) and
times N correction + undo pairs on it (NFR-013, p95 <= 1.5 s).

    python3 scripts/measure/live_tagging.py --cacert "$RA_DEV_STATE/root.crt" --runs 5 \
        --corrections 50 --json reports/goal/live-tagging.json

Exit 0 only when every step of every run passed and every timing met its target; 2 when it
refuses to start (disk floor). Route and field names: tagcontract.py, which mirrors
docs/architecture/api-sprint-02.md.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tagcontract as k
import taglib as t
from live_goal import create_upload, head_offset, new_match, patch
from livehttp import Client, sign_in, ssl_context
from measurelib import chunk_plan, effective_chunk


def upload_video(c: Client, match_id: str, data: bytes, timeout_s: float) -> dict[str, Any]:
    status, url = create_upload(c, match_id, len(data), "clip.mp4")
    if status != 201 or not url:
        return {"ok": False, "create_status": status}
    codes = [
        patch(c, url, o, data[o : o + n])
        for o, n in chunk_plan(len(data), effective_chunk(len(data), 8 << 20))
    ]
    ok_bytes = head_offset(c, url) == len(data) and all(s == 204 for s in codes)
    deadline, seen = time.perf_counter() + timeout_s, None
    while time.perf_counter() < deadline:
        seen = c.request("GET", f"/matches/{match_id}").json().get("status")
        if seen in ("video_received", "probe_failed"):
            break
        time.sleep(0.25)
    return {"ok": ok_bytes and seen == "video_received", "status": seen}


class Session:
    """One account's view of one match: the last version seen, the command timings."""

    def __init__(self, c: Client, match_id: str) -> None:
        self.c, self.match_id, self.version = c, match_id, 0
        self.timings: dict[str, list[float]] = {}

    def call(
        self, name: str, body: Any = None, *, version: int | None = None, rally_id: str = ""
    ) -> Any:
        method, p = k.path(name, match_id=self.match_id, rally_id=rally_id)
        headers = {}
        if method != "GET":
            headers[k.VERSION_HEADER] = str(self.version if version is None else version)
        r = self.c.request(method, p, json_body=body, headers=headers)
        self.timings.setdefault(name, []).append(r.ms)
        if r.status in (200, 201) and method != "GET":
            self.version = r.json().get(k.VERSION_KEY, self.version)
        return r

    def sheet(self) -> tuple[int, dict[str, Any]]:
        r = self.call("sheet")
        return r.status, (r.json() if r.status == 200 else {})


def _code(r: Any) -> str | None:
    """The refusal code from the api-sprint-00 §3 envelope ``{"error": {"code", ...}}``
    (api-sprint-02 §1.1, BE-D1-01). Any other body shape has no code."""
    try:
        error = r.json().get("error")
    except (ValueError, AttributeError):
        return None
    code = error.get("code") if isinstance(error, dict) else None
    return code if isinstance(code, str) else None


def _tag_all(
    s: Session, tags: list[dict[str, Any]], first: str, check_each: bool
) -> dict[str, Any]:
    started = s.call("start_game", {**k.START_GAME_BODY, "first_serving_side": first})
    expected = t.expected_rows(tags, first_serving_side=first)
    ids, diffs, to_current = [], [], []
    for i, tag in enumerate(tags):
        r = s.call("tag", tag)
        if r.status != 201:
            diffs.append(f"rally {i + 1}: status {r.status} {_code(r)}")
            break
        body = r.json()
        ids.append(body.get(k.RALLY_ID_KEY))
        if check_each:
            got = t.normalise_sheet(body.get(k.SHEET_KEY) or {})
            diffs += t.compare_rows(expected[: i + 1], got)
            t0 = time.perf_counter()
            _, sheet = s.sheet()  # NFR-017: last tag -> score sheet current
            to_current.append(time.perf_counter() - t0)
            if len(sheet.get("rows", [])) != i + 1:
                diffs.append(f"rally {i + 1}: sheet not current after the tag")
    return {
        "ok": started.status in (200, 201) and not diffs and len(ids) == len(tags),
        "start_status": started.status,
        "rally_ids": ids,
        "diffs": diffs[:20],
        "tag_to_sheet_s": [round(x, 3) for x in to_current],
    }


def journey(args: argparse.Namespace, data: bytes, ctx: Any) -> dict[str, Any]:
    c = Client(args.api, args.origin, ctx)
    steps: dict[str, Any] = {}
    s = None
    try:
        steps["sign_in"] = sign_in(c, args.mailpit)
        if not steps["sign_in"]["ok"]:
            return {"ok": False, "steps": steps}
        session_value = (c.cookie or "").partition("=")[2]

        early = new_match(c)
        r = Session(c, early or "").call("tag", t.JOURNEY_TAGS[0]) if early else None
        steps["tag_before_video_refused"] = {
            "ok": bool(r and r.status == 409 and _code(r) == k.NOT_READY),
            "status": r and r.status,
        }

        match_id = new_match(c)
        steps["video"] = (
            upload_video(c, match_id, data, args.result_timeout) if match_id else {"ok": False}
        )
        if not steps["video"]["ok"]:
            return {"ok": False, "steps": steps}
        s = Session(c, match_id)

        steps["tagging"] = _tag_all(s, t.JOURNEY_TAGS, "A", check_each=True)
        ids = steps["tagging"]["rally_ids"]
        if not steps["tagging"]["ok"]:
            return {"ok": False, "steps": steps}

        status, sheet = s.sheet()
        expected = t.expected_rows(t.JOURNEY_TAGS, first_serving_side="A")
        diffs = (
            t.compare_rows(expected, t.normalise_sheet(sheet)) if status == 200 else ["no sheet"]
        )
        steps["score_sheet"] = {
            "ok": not diffs
            and sheet.get("unofficial") is True
            and sheet.get("label") == t.UNOFFICIAL_LABEL
            and bool(sheet.get("rules_version")),
            "status": status,
            "diffs": diffs,
            "label": sheet.get("label"),
            "rules_version": sheet.get("rules_version"),
        }
        before = t.canonical_bytes(sheet)

        bad = dict(
            t.JOURNEY_TAGS[5],
            ending="unforced_error",
            responsible_player="A2",
            start_ms=t.JOURNEY_TAGS[5]["end_ms"] + 1,
            end_ms=t.JOURNEY_TAGS[5]["end_ms"] + 500,
        )
        r = s.call("tag", bad)
        steps["wrong_side_refused"] = {
            "ok": r.status == 422
            and _code(r) == k.INVALID_OUTCOME
            and t.canonical_bytes(s.sheet()[1]) == before,
            "status": r.status,
            "code": _code(r),
        }

        r = s.call(
            "tag", bad | {"ending": "winner", "responsible_player": None}, version=s.version - 1
        )
        steps["stale_version_refused"] = {
            "ok": r.status == 409 and _code(r) == k.STALE,
            "status": r.status,
        }

        r = s.call("correct", {"field": "winning_side", "value": "A"}, rally_id=ids[1])
        corrected = t.expected_rows(
            t.with_winner(t.JOURNEY_TAGS, rally=2, side="A"), first_serving_side="A"
        )
        got = r.json().get(k.SHEET_KEY, {}) if r.status == 200 else {}
        diffs = t.compare_rows(corrected, t.normalise_sheet(got)) if got else ["no sheet"]
        marked = [row.get(k.CORRECTED_KEY) for row in got.get("rows", [])]
        hist = s.call("history").json().get(k.HISTORY_ITEMS, [])
        steps["correction"] = {
            "ok": r.status == 200
            and not diffs
            and marked[:3] == [False, True, False]
            and any(
                h.get("field") == "winning_side"
                and h.get("old_value") == "B"
                and h.get("new_value") == "A"
                for h in hist
            ),
            "status": r.status,
            "diffs": diffs,
            "corrected_markers": marked,
            "history_len": len(hist),
        }

        r = s.call("undo")
        after = t.canonical_bytes(s.sheet()[1])
        hist = s.call("history").json().get(k.HISTORY_ITEMS, [])
        steps["undo_byte_identical"] = {
            "ok": r.status == 200
            and after == before
            and [h.get("kind") for h in hist][-2:] == ["correction", "undo"],
            "status": r.status,
            "identical": after == before,
            "history_kinds": [h.get("kind") for h in hist],
        }

        second = new_match(c)
        v2 = upload_video(c, second, data, args.result_timeout) if second else {"ok": False}
        s2 = Session(c, second or "")
        tagged = _tag_all(s2, t.CONFLICT_TAGS, "A", check_each=False) if v2["ok"] else {"ok": False}
        r = (
            s2.call(
                "correct",
                {"field": "winning_side", "value": "A"},
                rally_id=tagged.get("rally_ids", [""] * 14)[t.CONFLICT_FLIP - 1],
            )
            if tagged["ok"]
            else None
        )
        exp = t.expected_rows(
            t.with_winner(t.CONFLICT_TAGS, rally=t.CONFLICT_FLIP, side="A"), first_serving_side="A"
        )
        got = r.json().get(k.SHEET_KEY, {}) if r is not None and r.status == 200 else {}
        diffs = t.compare_rows(exp, t.normalise_sheet(got)) if got else ["no sheet"]
        steps["conflict_kept_needs_verification"] = {
            "ok": not diffs,
            "provisional": True,
            "diffs": diffs,
            "needs_decision": [row["number"] for row in exp if row["marker"] == "needs_decision"],
        }

        r = s.call("media", rally_id=ids[2])
        media = r.json() if r.status == 200 else {}
        url = urllib.parse.urljoin(args.origin + "/", media.get(k.MEDIA_URL, ""))
        problems = (
            t.media_url_problems(url, media.get(k.MEDIA_TTL), session_value)
            if media
            else ["no media"]
        )
        ranged = _fetch(url, ctx, {"Range": "bytes=0-1023"}) if media else None
        tampered = (
            _fetch(url[:-1] + ("0" if url[-1] != "0" else "1"), ctx, {"Range": "bytes=0-1023"})
            if media
            else None
        )
        steps["media_link"] = {
            "ok": not problems
            and ranged == 206
            and tampered in (401, 403)
            and media.get(k.MEDIA_START) == t.JOURNEY_TAGS[2]["start_ms"],
            "status": r.status,
            "problems": problems,
            "range_status": ranged,
            "tampered_status": tampered,
            "ttl_s": media.get(k.MEDIA_TTL),
        }

        other = Client(args.api, args.origin, ctx)
        try:
            sign_in(other, args.mailpit)
            codes = {
                name: other.request(*k.path(name, match_id=match_id, rally_id=ids[2])).status
                for name in ("sheet", "history", "media")
            }
        finally:
            other.close()
        steps["other_account_404"] = {"ok": set(codes.values()) == {404}, "statuses": codes}

        out = c.request("POST", "/auth/sign-out")
        steps["sign_out"] = {"ok": out.status == 204 and c.request("GET", "/me").status == 401}
    finally:
        c.close()
    timings = s.timings if s else {}
    return {
        "ok": all(v.get("ok") for v in steps.values()),
        "steps": steps,
        "tag_ms": [round(x, 1) for x in timings.get("tag", [])],
    }


def _fetch(url: str, ctx: Any, headers: dict[str, str]) -> int | None:
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        return None  # only http(s) media links are fetched
    try:
        with urllib.request.urlopen(  # noqa: S310 (scheme checked above)
            urllib.request.Request(url, headers=headers),  # noqa: S310
            timeout=30,
            context=ctx,
        ) as r:
            r.read(2048)
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError, ValueError):
        return None


def corrections(args: argparse.Namespace, data: bytes, ctx: Any) -> dict[str, Any]:
    """NFR-013: correction command -> server-confirmed state on a decided 3-game match."""
    c = Client(args.api, args.origin, ctx)
    try:
        if not sign_in(c, args.mailpit)["ok"]:
            return {"ok": False, "reason": "sign-in"}
        match_id = new_match(c)
        if not match_id or not upload_video(c, match_id, data, args.result_timeout)["ok"]:
            return {"ok": False, "reason": "video"}
        s = Session(c, match_id)
        games = t.three_game_script(seed=args.seed)
        all_tags = t.with_times(
            [tag for g in games for tag in g["tags"]], duration_ms=args.video_ms
        )
        ids, pos = [], 0
        for g in games:
            part = all_tags[pos : pos + len(g["tags"])]
            pos += len(g["tags"])
            tagged = _tag_all(s, part, g["first_serving_side"], check_each=False)
            if not tagged["ok"]:
                return {"ok": False, "reason": "tagging", "detail": tagged}
            ids += tagged["rally_ids"]
        _, baseline = s.sheet()
        base_bytes, failures, samples = t.canonical_bytes(baseline), 0, []
        for i in range(args.corrections):
            j = (i * 7) % len(ids)
            side = "B" if all_tags[j]["winning_side"] == "A" else "A"
            t0 = time.perf_counter()
            r1 = s.call("correct", {"field": "winning_side", "value": side}, rally_id=ids[j])
            samples.append((time.perf_counter() - t0) * 1000)
            t0 = time.perf_counter()
            r2 = s.call("undo")
            samples.append((time.perf_counter() - t0) * 1000)
            failures += (r1.status != 200) + (r2.status != 200)
        restored = t.canonical_bytes(s.sheet()[1]) == base_bytes
        summary = t.timing_summary(
            samples, max_p95_ms=args.max_correction_p95_ms, min_n=2 * args.corrections
        )
        return {
            "ok": summary["ok"] and failures == 0 and restored,
            "rallies": len(ids),
            "games": len(games),
            "failures": failures,
            "restored_byte_identical": restored,
            "timing": summary,
        }
    finally:
        c.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--api", default="https://localhost:3000/api")
    p.add_argument("--origin", default="https://localhost:3000")
    p.add_argument("--mailpit", default="http://127.0.0.1:8025")
    p.add_argument("--cacert")
    p.add_argument("--insecure-loopback", action="store_true")
    p.add_argument("--file", default="fixtures/clips/synthetic-60s/clip.mp4")
    p.add_argument("--video-ms", type=int, default=60_000, help="fixture duration")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--corrections", type=int, default=0, help="correction+undo pairs (NFR-013)")
    p.add_argument("--seed", type=int, default=20261005)
    p.add_argument("--max-correction-p95-ms", type=float, default=1500.0)
    p.add_argument("--max-tag-to-sheet-p95-s", type=float, default=5.0)
    p.add_argument("--result-timeout", type=float, default=120.0)
    p.add_argument("--json", type=Path)
    p.add_argument("--min-free-gb", type=int, default=10)
    args = p.parse_args(argv)
    free_gb = shutil.disk_usage("/").free // 1024**3
    if free_gb < args.min_free_gb:
        print(
            f"live_tagging: only {free_gb} GB free on /, need >= {args.min_free_gb} GB; "
            "prune first (bash scripts/disk-precheck.sh, docs/ops/disk-and-prune.md)",
            file=sys.stderr,
        )
        return 2
    data = Path(args.file).read_bytes()
    ctx = ssl_context(args.cacert, args.insecure_loopback)
    runs = []
    for i in range(args.runs):
        try:
            runs.append(journey(args, data, ctx))
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            runs.append({"ok": False, "steps": {}, "error": repr(exc)})  # fail closed
        print(f"run {i + 1}/{args.runs}: {'PASS' if runs[-1]['ok'] else 'FAIL'}", file=sys.stderr)
    to_sheet = [x for r in runs for x in r["steps"].get("tagging", {}).get("tag_to_sheet_s", [])]
    tag_ms = [x for r in runs for x in r.get("tag_ms", [])]
    summary: dict[str, Any] = {
        "runs": len(runs),
        "runs_passed": sum(1 for r in runs if r["ok"]),
        "tag_to_sheet": t.timing_summary(
            [x * 1000 for x in to_sheet],
            max_p95_ms=args.max_tag_to_sheet_p95_s * 1000,
            min_n=len(runs) * 6,
        ),
        "tag_server_ms": t.timing_summary(
            tag_ms, max_p95_ms=1e9, min_n=1
        ),  # reported, not a target
        "disk_free_gb_start": free_gb,
    }
    if args.corrections:
        try:
            summary["corrections"] = corrections(args, data, ctx)
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            summary["corrections"] = {"ok": False, "error": repr(exc)}
    summary["disk_free_gb_end"] = shutil.disk_usage("/").free // 1024**3
    ok = (
        bool(runs)
        and summary["runs_passed"] == len(runs)
        and summary["tag_to_sheet"]["ok"]
        and (not args.corrections or summary["corrections"]["ok"])
    )
    summary["ok"] = ok
    print(json.dumps(summary, indent=2, default=str))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps({"summary": summary, "runs": runs}, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
