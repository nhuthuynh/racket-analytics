"""Binds tests/features/live_plan_harness.feature (QA-HARNESS-4a; G04-01..G04-03).

`live_plan.main` runs over real TLS against a local stub of the api-sprint-04 routes (a
throwaway self-signed certificate per module) and the fake Mailpit of test_livehttp_mailpit.py.
The stub serves the statslib reference as GET stats and evidence, and a plan_fixtures plan that
each scenario breaks in one way. Standard library plus pytest-bdd; no product imports.
"""

from __future__ import annotations

import json
import secrets
import ssl
import subprocess
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import plan_fixtures as pf
import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from test_livehttp_mailpit import FakeMailpit

pytestmark = pytest.mark.integration
scenarios("live_plan_harness.feature")
live = pf.load("live_plan")
WANT = live.pl.ranking([{"first_serving_side": "A", "tags": pf.s.STATS_TAGS}], "A")
STATS = pf.s.as_api_shape(pf.REF) | {"unofficial": True, "label": live.t.UNOFFICIAL_LABEL}


def _over_budget(p: dict, n: int) -> None:
    p["sessions"][0]["assignments"][2]["minutes"] = 20


def _no_warm_up(p: dict, n: int) -> None:
    p["sessions"][0]["assignments"].reverse()


def _wrong_value(p: dict, n: int) -> None:
    p["sessions"][0]["assignments"][1]["citation"]["value"] = 0.99


def _drifts(p: dict, n: int) -> None:
    p["sessions"][0]["assignments"][1]["minutes"] = 12 - n % 2
    p["content_digest"] = f"sha256:{n}"


DEFECTS = {
    "keeps every rule": lambda p, n: None,
    "has a session over its 30-minute budget": _over_budget,
    "starts a session without a warm-up": _no_warm_up,
    "cites a value the stats do not show": _wrong_value,
    "changes its content on every generation": _drifts,
}


class Stub:
    """The routes the journey calls; plan routes answer 404 to any account but the owner."""

    def __init__(self, tls: tuple[str, str], mailpit: FakeMailpit, defect: str) -> None:
        self.mailpit, self.defect, self.seen = mailpit, DEFECTS[defect], 0
        self.owner, self.current, self.keys, self.posts = None, {}, set(), 0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_: Any) -> None:
                return

            def reply(self, status: int, body: Any = None, **headers: str) -> None:
                data = b"" if body is None else json.dumps(body).encode()
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name.replace("_", "-"), value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def route(self) -> None:
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                outer.seen += 1
                outer.answer(self, self.path.removeprefix("/api").split("?")[0])

            do_GET = do_POST = do_PATCH = do_HEAD = route

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(tls[1], tls[0])
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.socket = ctx.wrap_socket(self.server.socket, server_side=True)
        self.base = f"https://localhost:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def answer(self, h: Any, p: str) -> None:
        m, me, part = h.command, h.headers.get("Cookie"), p.split("/")
        if p == "/auth/links":
            self.mailpit.deliver(secrets.token_urlsafe(32))
            return h.reply(202, {})
        if p == "/auth/exchange":
            return h.reply(200, {}, Set_Cookie=f"__Host-racket_session={uuid.uuid4().hex}")
        if p.startswith("/matches/m1/stats/"):
            items = [{"number": r, "rally_id": f"r{r}"} for r in pf.REF[part[4]]["A"]["rallies"]]
            return h.reply(200, {"items": items, "total": len(items), "next_cursor": None})
        if p == "/matches/m1/stats":
            return h.reply(200, STATS)
        if p == "/me/plan" and m == "POST":
            self.owner, self.posts, self.current = me, self.posts + 1, pf.plan(WANT)
            self.defect(self.current, self.posts)
            return h.reply(201, self.current)
        if p.startswith("/me/plan") and me != self.owner:
            return h.reply(404, {"error": {"code": "not_found"}})
        if p == "/me/plan":
            return h.reply(200, self.current)
        if p.endswith("/done"):
            replayed = h.headers["Idempotency-Key"] in self.keys
            self.keys.add(h.headers["Idempotency-Key"])
            for sess in self.current["sessions"]:
                sess["done"] = sess["done"] or sess["id"] == part[4]
            return h.reply(200, {"done": True, "plan_version": 2, "replayed": replayed})
        if p.endswith("/swap"):
            sess = next(x for x in self.current["sessions"] if x["id"] == part[4][:2])
            sess["assignments"][int(part[4][-1]) - 1]["drill"] = pf.ALT
            return h.reply(200, sess | {"plan_version": 3})
        if p.endswith("/uploads"):
            return h.reply(201, {}, Location="/api/matches/m1/uploads/u1")
        if m in ("PATCH", "HEAD"):
            return h.reply(204 if m == "PATCH" else 200, None, Upload_Offset="4")
        if m == "POST":
            return h.reply(201, {"id": "m1", "version": 1, "rally_id": "r1"})
        return h.reply(200, {"status": "video_received"})

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture(scope="module")
def tls(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    d = tmp_path_factory.mktemp("tls")
    key, crt = str(d / "key.pem"), str(d / "crt.pem")
    cmd = ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1"]
    cmd += ["-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"]
    subprocess.run([*cmd, "-keyout", key, "-out", crt], check=True, capture_output=True)
    return key, crt


@pytest.fixture
def world(tmp_path, tls):
    mailpit = FakeMailpit()
    drills = tmp_path / "drills"
    for d in pf.library().values():
        (drills / d["id"]).mkdir(parents=True)
        (drills / d["id"] / "v1.json").write_text(json.dumps(d))
    (tmp_path / "clip.mp4").write_bytes(b"\x00" * 4)
    w = {"tmp": tmp_path, "tls": tls, "mailpit": mailpit, "base": "https://localhost:1"}
    w["args"] = ["--cacert", tls[1], "--mailpit", mailpit.url, "--drills", str(drills)]
    w["args"] += ["--file", str(tmp_path / "clip.mp4"), "--json", str(tmp_path / "out.json")]
    yield w
    mailpit.close()
    if "stub" in w:
        w["stub"].close()


@given(parsers.parse("a stub stack whose plan {defect}"))
def _stub(world, defect):
    world["stub"] = Stub(world["tls"], world["mailpit"], defect)
    world["base"] = world["stub"].base


@given("no stack listening")
def _nothing(world):
    assert "stub" not in world


def _main(world, *extra: str) -> None:
    world["rc"] = live.main(["--base-url", world["base"], *world["args"], *extra])
    out = world["tmp"] / "out.json"
    world["report"] = json.loads(out.read_text()) if out.exists() else None


@when(parsers.parse("the plan harness runs {runs:d} run with determinism {k:d}"))
def _runs(world, runs, k):
    _main(world, "--runs", str(runs), "--determinism", str(k))


@when("the plan harness runs with a disk floor above the free space")
def _floor(world):
    _main(world, "--min-free-gb", "1000000")


@when(parsers.parse("the plan harness runs the load mode at {rps:d} RPS for 1 second"))
def _load(world, rps):
    _main(world, "--load", "--rps", str(rps), "--duration", "1")


@then(parsers.parse("it exits {rc:d}"))
def _rc(world, rc):
    assert world["rc"] == rc, json.dumps(world["report"], indent=1)[:3000]


@then(parsers.parse('the "{step}" step names "{rule}"'))
def _names(world, step, rule):
    assert rule in json.dumps(world["report"]["runs"][0][step]["problems"])


@then("the stub saw no request")
def _no_request(world):
    assert world["stub"].seen == 0


@then("every step passed, with 4 generation timings, 1 done timing and 9 reference rows")
def _all_passed(world):
    summary, (run,) = world["report"]["summary"], world["report"]["runs"]
    assert [k for k, v in run.items() if not v["ok"]] == []
    assert len(run) == 11
    assert (summary["generate"]["n"], summary["done_visible"]["n"]) == (4, 1)
    assert summary["reference"] == {"comparisons": 9, "mismatches": [], "ok": True}


@then("the load summary counts 20 requests and none unexpected")
def _load_summary(world):
    summary = world["report"]["summary"]
    assert (summary["requests"], summary["status_unexpected"], summary["ok"]) == (20, 0, True)
