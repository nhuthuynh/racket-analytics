#!/usr/bin/env python3
"""Sprint 1 goal journey, live and in real time (goal scorecard G01-01, G01-05, G01-06).

Runs the user-visible Sprint 1 goal against a running local stack, through the same origin a
browser uses (default https://localhost:3000/api, ADR 0029), as a fresh account per run:

  1. magic-link sign-in via Mailpit (ST-013), then GET /me
  2. a doubles match with 4 nicknames and one "me" (ST-016)
  3. tus upload to >= 40 %, connection dropped, HEAD, resume from the server offset (ST-017)
  4. a damaged chunk is refused with 460 and the offset is kept (ST-017)
  5. tus upload to the end, timed (throughput)
  6. "Video received" with facts (time from the final byte to the result)
  7. invalid files refused (ST-018): 12 GB Upload-Length -> 413; a PDF named .mp4 -> 415
  8. sign-out, then the old session is refused (ST-014)

    python3 scripts/measure/live_goal.py --file fixtures/clips/synthetic-60s/clip.mp4 \
        --runs 5 --json reports/goal/live-goal.json

Exit 0 only when every step of every run passed. Timings and throughput are in the JSON.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from livehttp import Client, sign_in, ssl_context
from measurelib import (
    checksum_header,
    chunk_plan,
    effective_chunk,
    percentile,
    throughput_mbps,
    tus_metadata,
)

TUS = {"Tus-Resumable": "1.0.0"}
PDF = b"%PDF-1.7\n" + b"0" * 4096
DOUBLES = [
    {"slot": "A1", "nickname": "Ivy", "is_me": True},
    {"slot": "A2", "nickname": "Dana", "is_me": False},
    {"slot": "B1", "nickname": "Carlos", "is_me": False},
    {"slot": "B2", "nickname": "Sam", "is_me": False},
]


def new_match(c: Client) -> str | None:
    body = {
        "format": "doubles",
        "scoring_system": "side_out",
        "played_on": dt.date.today().isoformat(),
        "participants": DOUBLES,
    }
    r = c.request("POST", "/matches", json_body=body)
    return r.json()["id"] if r.status == 201 else None


def create_upload(c: Client, match_id: str, length: int, name: str) -> tuple[int, str | None]:
    r = c.request(
        "POST",
        f"/matches/{match_id}/uploads",
        headers={
            **TUS,
            "Upload-Length": str(length),
            "Upload-Metadata": tus_metadata(filename=name),
        },
    )
    return r.status, r.headers.get("Location")


def patch(c: Client, url: str, offset: int, data: bytes, checksum: str | None = None) -> int:
    headers = {
        **TUS,
        "Upload-Offset": str(offset),
        "Content-Type": "application/offset+octet-stream",
        "Upload-Checksum": checksum or checksum_header(data),
    }
    return c.request("PATCH", url, body=data, headers=headers).status


def head_offset(c: Client, url: str) -> int | None:
    r = c.request("HEAD", url, headers=TUS)
    return int(r.headers["Upload-Offset"]) if r.status == 200 else None


def one_run(args: argparse.Namespace, data: bytes) -> dict[str, Any]:
    ctx = ssl_context(args.cacert, args.insecure_loopback)
    c = Client(args.api, args.origin, ctx)
    steps: dict[str, Any] = {}
    try:
        steps["sign_in"] = sign_in(c, args.mailpit)
        if not steps["sign_in"]["ok"]:
            return {"ok": False, "steps": steps}
        me = c.request("GET", "/me")
        steps["me"] = {"ok": me.status == 200, "status": me.status}

        match_id = new_match(c)
        steps["match"] = {"ok": match_id is not None, "match_id": match_id}
        if not match_id:
            return {"ok": False, "steps": steps}
        status, url = create_upload(c, match_id, len(data), Path(args.file).name)
        steps["upload_create"] = {"ok": status == 201 and bool(url), "status": status}
        if not url:
            return {"ok": False, "steps": steps}

        chunk = effective_chunk(len(data), args.chunk)
        plan = chunk_plan(len(data), chunk)
        cut = next(i for i, (o, n) in enumerate(plan) if o + n >= 0.4 * len(data)) + 1
        sent = 0.0
        t0 = time.perf_counter()
        codes = [patch(c, url, o, data[o : o + n]) for o, n in plan[:cut]]
        sent += time.perf_counter() - t0
        c.close()  # the connection drops at >= 40 %
        resumed_from = head_offset(c, url)
        expected = plan[cut - 1][0] + plan[cut - 1][1]
        steps["resume"] = {
            "ok": all(s == 204 for s in codes) and resumed_from == expected < len(data),
            "percent_at_drop": round(100 * expected / len(data), 1),
            "server_offset": resumed_from,
        }
        if resumed_from is None:
            return {"ok": False, "steps": steps}
        rest = chunk_plan(len(data), chunk, start=resumed_from)
        steps["damaged_chunk"] = {"ok": False, "status": None}
        if rest:
            o, n = rest[0]
            bad = patch(c, url, o, data[o : o + n], checksum=checksum_header(b"not this chunk"))
            steps["damaged_chunk"] = {
                "ok": bad == 460 and head_offset(c, url) == resumed_from,
                "status": bad,
            }
        t1 = time.perf_counter()
        codes = [patch(c, url, o, data[o : o + n]) for o, n in rest]
        sent += time.perf_counter() - t1
        t_final = time.perf_counter()
        final = head_offset(c, url)
        steps["upload_complete"] = {
            "ok": all(s == 204 for s in codes) and final == len(data),
            "bytes": len(data),
            "transfer_s": round(sent, 3),
            "throughput_mbps": round(throughput_mbps(len(data), sent), 1),
        }

        status_seen, facts = None, None
        deadline = t_final + args.result_timeout
        while time.perf_counter() < deadline:
            status_seen = c.request("GET", f"/matches/{match_id}").json().get("status")
            if status_seen in ("video_received", "probe_failed"):
                media = c.request("GET", f"/matches/{match_id}/media")
                if media.status == 200:
                    facts = media.json()
                    break
                if status_seen == "probe_failed":
                    break
            time.sleep(0.25)
        steps["result"] = {
            "ok": status_seen == "video_received" and facts is not None,
            "status": status_seen,
            "final_byte_to_facts_s": round(time.perf_counter() - t_final, 3),
            "facts": facts,
        }

        refused_id = new_match(c)
        big, _ = create_upload(c, refused_id or "", 12_000_000_000, "big.mp4")
        pdf_status, pdf_url = create_upload(c, refused_id or "", len(PDF), "match.mp4")
        pdf_patch = patch(c, pdf_url, 0, PDF) if pdf_url else None
        refused = c.request("GET", f"/matches/{refused_id}").json() if refused_id else {}
        steps["invalid_refused"] = {
            "ok": big == 413 and pdf_patch == 415 and refused.get("status") != "video_received",
            "twelve_gb_status": big,
            "pdf_create_status": pdf_status,
            "pdf_patch_status": pdf_patch,
            "match_status_after": refused.get("status"),
        }

        out = c.request("POST", "/auth/sign-out")
        after = c.request("GET", "/me")
        steps["sign_out"] = {
            "ok": out.status == 204 and after.status == 401,
            "sign_out_status": out.status,
            "me_after_status": after.status,
        }
    finally:
        c.close()
    return {"ok": all(s.get("ok") for s in steps.values()), "steps": steps}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--api", default="https://localhost:3000/api", help="API base URL")
    p.add_argument("--origin", default="https://localhost:3000", help="Origin header (allowlist)")
    p.add_argument("--mailpit", default="http://127.0.0.1:8025")
    p.add_argument("--cacert", help="dev root CA (web-tls root.crt)")
    p.add_argument("--insecure-loopback", action="store_true", help="skip TLS checks on loopback")
    p.add_argument("--file", default="fixtures/clips/synthetic-60s/clip.mp4")
    p.add_argument("--chunk", type=int, default=8 * 1024 * 1024, help="bytes (ADR 0019: 8 MiB)")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--result-timeout", type=float, default=120.0, help="seconds")
    p.add_argument("--json", type=Path)
    args = p.parse_args(argv)
    data = Path(args.file).read_bytes()
    runs = []
    for i in range(args.runs):
        run = one_run(args, data)
        runs.append(run)
        print(f"run {i + 1}/{args.runs}: {'PASS' if run['ok'] else 'FAIL'}", file=sys.stderr)

    def series(step: str, key: str) -> list[float]:
        found = (r["steps"].get(step, {}).get(key) for r in runs)
        return [v for v in found if v is not None]

    sign_in_s = series("sign_in", "sign_in_s")
    result_s = series("result", "final_byte_to_facts_s")
    mbps = series("upload_complete", "throughput_mbps")
    summary = {
        "runs": len(runs),
        "runs_passed": sum(1 for r in runs if r["ok"]),
        "sign_in_p95_s": percentile(sign_in_s, 95) if sign_in_s else None,
        "final_byte_to_facts_p95_s": percentile(result_s, 95) if result_s else None,
        "throughput_min_mbps": min(mbps) if mbps else None,
        "file": args.file,
        "file_bytes": len(data),
        "api": args.api,
    }
    text = json.dumps({"summary": summary, "runs": runs}, indent=2, default=str)
    print(json.dumps(summary, indent=2))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    return 0 if summary["runs_passed"] == len(runs) and runs else 1


if __name__ == "__main__":
    sys.exit(main())
