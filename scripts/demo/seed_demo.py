#!/usr/bin/env python3
"""`make demo` (MVP-03): seed a ready-to-explore demo match into a running dev stack.

Through the public HTTP API only, as the browser does (https://localhost:3000/api, ADR 0029):

 1. refuses unless the stack is the dev profile: APP_ENV=dev in the env file, and the API
    answers GET /dev/users (the /dev/* routes exist only with dev sign-in enabled);
 2. signs in as the dev user Ivy (the "Sign in as Ivy" button);
 3. reuses a complete "Demo match" if Ivy has one (re-running adds nothing); otherwise creates
    a doubles match, uploads the 60 s H.264 fixture by tus and waits for "Video received";
 4. starts game 1 and tags the 12 rallies of demoplan.rally_plan (POST .../games and
    POST .../rallies with If-Match versions), then checks the stats have metrics;
 5. prints the stats page to open and who to sign in as.

    python3 scripts/demo/seed_demo.py --base-url https://localhost:3000 --cacert root.crt

Exit 0 seeded or already seeded; 1 a step failed; 3 refused (not a dev stack).
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "scripts" / "measure"))
import demoplan as plan  # noqa: E402
from livehttp import Client, Reply, ssl_context  # noqa: E402
from measurelib import checksum_header, chunk_plan, tus_metadata  # noqa: E402

REFUSED, FAILED = 3, 1
TUS = {"Tus-Resumable": "1.0.0"}
CHUNK = 4 << 20
DEFAULT_CLIP = REPO / "fixtures" / "clips" / "synthetic-60s" / "clip.mp4"


class StepFailed(Exception):
    pass


def _expect(r: Reply, status: int, what: str) -> Any:
    if r.status != status:
        raise StepFailed(f"{what}: HTTP {r.status} {r.body[:300]!r}")
    return r.json() if r.body else None


def _version(r: Reply) -> int:
    etag = (r.headers.get("ETag") or "").strip('W/"')
    if not etag.isdigit():
        raise StepFailed(f"no version in ETag {r.headers.get('ETag')!r}")
    return int(etag)


def sign_in(c: Client, username: str) -> str | None:
    """None when signed in; otherwise why the stack is refused."""
    users = c.request("GET", "/dev/users")
    if users.status == 404:
        return "dev sign-in is disabled on this stack (GET /dev/users is 404)"
    names = [u.get("username") for u in (_expect(users, 200, "GET /dev/users") or {})["items"]]
    if username not in names:
        return f"no dev user {username!r} on this stack (found {names})"
    _expect(c.request("POST", "/dev/sign-in", json_body={"username": username}), 204, "sign-in")
    return None


def demo_matches(c: Client) -> list[plan.DemoMatch]:
    items = _expect(c.request("GET", "/matches?limit=50"), 200, "GET /matches")["items"]
    found = []
    for m in items:
        if not plan.is_demo_title(m["title"]):
            continue
        rallies = 0
        if m["status"] == "video_received":
            sheet = c.request("GET", f"/matches/{m['id']}/score-sheet")
            rallies = len(sheet.json().get("rows", [])) if sheet.status == 200 else 0
        found.append(plan.DemoMatch(m["id"], m["title"], m["status"], rallies))
    return found


def upload(c: Client, match_id: str, data: bytes, timeout_s: float) -> int:
    """tus upload; waits for "Video received" and returns the probed duration in ms."""
    created = c.request(
        "POST",
        f"/matches/{match_id}/uploads",
        headers={**TUS, "Upload-Length": str(len(data)),
                 "Upload-Metadata": tus_metadata(filename="demo-match.mp4")},
    )  # fmt: skip
    _expect(created, 201, "create upload")
    url = created.headers.get("Location") or ""
    for offset, n in chunk_plan(len(data), CHUNK):
        chunk = data[offset : offset + n]
        headers = {**TUS, "Upload-Offset": str(offset), "Upload-Checksum": checksum_header(chunk),
                   "Content-Type": "application/offset+octet-stream"}  # fmt: skip
        _expect(c.request("PATCH", url, body=chunk, headers=headers), 204, f"upload @{offset}")
    deadline, status = time.monotonic() + timeout_s, None
    while time.monotonic() < deadline:
        match = _expect(c.request("GET", f"/matches/{match_id}"), 200, "GET match")
        status = match["status"]
        if status == "video_received" and match.get("media"):
            return int(match["media"]["duration_ms"])
        if status == "probe_failed":
            break
        time.sleep(0.5)
    raise StepFailed(f"the video was not received (status {status})")


def tag_game(c: Client, match_id: str, rallies: list[dict[str, Any]]) -> None:
    version = _version(c.request("GET", f"/matches/{match_id}/score-sheet"))
    start = {"first_serving_side": plan.FIRST_SERVING_SIDE, "ends_switched": False}
    r = c.request("POST", f"/matches/{match_id}/games", json_body=start,
                  headers={"If-Match": str(version)})  # fmt: skip
    version = _expect(r, 201, "start game 1")["version"]
    for number, rally in enumerate(rallies, start=1):
        r = c.request("POST", f"/matches/{match_id}/rallies", json_body=rally,
                      headers={"If-Match": str(version)})  # fmt: skip
        version = _expect(r, 201, f"tag rally {number}")["version"]


@dataclass(frozen=True)
class Seeded:
    title: str
    match_id: str
    tagged: int  # rallies tagged by this run; 0 when the demo match was reused


def seed(c: Client, args: argparse.Namespace) -> Seeded:
    action = plan.choose(demo_matches(c), planned=plan.RALLIES, new=args.new)
    if action.match_id is not None:  # reuse
        return Seeded(action.title, action.match_id, 0)
    body = {"title": action.title, "format": "doubles", "scoring_system": "side_out",
            "participants": plan.DEMO_PARTICIPANTS}  # fmt: skip
    match_id = _expect(c.request("POST", "/matches", json_body=body), 201, "create match")["id"]
    duration_ms = upload(c, match_id, Path(args.file).read_bytes(), args.probe_timeout)
    rallies = plan.rally_plan(duration_ms)
    tag_game(c, match_id, rallies)
    return Seeded(action.title, match_id, len(rallies))


def check_stats(c: Client, match_id: str) -> int:
    stats = _expect(c.request("GET", f"/matches/{match_id}/stats"), 200, "GET stats")
    metrics = stats.get("metrics") or {}
    if not metrics:
        raise StepFailed("the stats have no published metric")
    return len(metrics)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base-url", default="https://localhost:3000", help="web origin (web-tls)")
    p.add_argument("--cacert", help="the stack's web-tls root certificate (ADR 0029)")
    p.add_argument("--env-file", default=str(REPO / "infra" / ".env"))
    p.add_argument("--user", default=plan.DEMO_USER)
    p.add_argument("--file", default=str(DEFAULT_CLIP), help="H.264 MP4 to upload")
    p.add_argument("--new", action="store_true", help='always create "Demo match (n)"')
    p.add_argument("--probe-timeout", type=float, default=180.0)
    args = p.parse_args(argv)

    env_file = Path(args.env_file)
    env = plan.parse_env_file(env_file.read_text()) if env_file.is_file() else {}
    why = plan.refusal(env)
    if why:
        print(f"make demo refused: {why}", file=sys.stderr)
        return REFUSED

    base = args.base_url.rstrip("/")
    c = Client(f"{base}/api", base, ssl_context(args.cacert, False))
    try:
        why = sign_in(c, args.user)
        if why:
            print(f"make demo refused: {why}", file=sys.stderr)
            return REFUSED
        seeded = seed(c, args)
        metrics = check_stats(c, seeded.match_id)
    except (StepFailed, OSError) as e:
        print(f"make demo failed: {e}. Is the stack up (`make up`)?", file=sys.stderr)
        return FAILED
    finally:
        c.close()

    done = (f"created with {seeded.tagged} tagged rallies" if seeded.tagged
            else "already seeded; nothing added (use --new for another)")  # fmt: skip
    print(f"{seeded.title}: {done}; {metrics} published metrics.")
    print(f"Open {plan.stats_url(base, seeded.match_id)}")
    print(f"Sign in as {plan.DEMO_USER_LABEL} (the 'Sign in as {plan.DEMO_USER_LABEL}' button).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
