"""Helpers for CI-OBJSTORE-PORT-RACE: run the real scripts/dev-objectstore.sh against a
stand-in weed binary that collides on demand (no SeaweedFS, no network beyond 127.0.0.1).

The stand-in records each invocation's port flags, then either fails the way SeaweedFS does
(same log wording as main run 40874800467) or serves 200 on its -s3.port so `start` can create
the bucket and return.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from conftest import SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "dev-objectstore.sh"

FAKE_WEED = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import http.server, json, os, sys
    from pathlib import Path

    work = Path(os.environ["FAKE_WEED_DIR"])
    ports = {}
    for arg in sys.argv[1:]:
        if arg.startswith("-") and "=" in arg and "port" in arg.split("=", 1)[0]:
            k, v = arg[1:].split("=", 1)
            ports[k] = int(v)
    with open(work / "calls.jsonl", "a") as f:
        f.write(json.dumps(ports) + "\\n")
    calls = sum(1 for _ in open(work / "calls.jsonl"))
    mode = os.environ.get("FAKE_WEED_MODE", "ok")
    if mode == "fail":
        print("F1029 server.go:1] invalid -dir: permission denied", file=sys.stderr)
        sys.exit(1)
    if mode.startswith("collide:") and calls <= int(mode.split(":", 1)[1]):
        print(
            "F1029 filer.go:1] Filer listener error: listen tcp 127.0.0.1:%d: "
            "bind: address already in use" % ports.get("filer.port", 0),
            file=sys.stderr,
        )
        sys.exit(1)

    class H(http.server.BaseHTTPRequestHandler):
        def _ok(self):
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
        do_PUT = do_GET = do_HEAD = _ok
        def log_message(self, *a):
            pass

    http.server.HTTPServer(("127.0.0.1", ports["s3.port"]), H).serve_forever()
    """
)


@dataclass
class FakeStore:
    work: Path
    state: Path
    mode: str = "ok"

    @property
    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith(("S3_", "RA_"))}
        env.update(
            WEED_BIN=str(self.work / "weed"),
            FAKE_WEED_DIR=str(self.work),
            FAKE_WEED_MODE=self.mode,
            RA_DEV_STATE=str(self.state),
            TMPDIR=str(self.work),
        )
        return env

    def run(self, *args: str, timeout: float = 120) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=timeout,
            check=False,
        )

    def calls(self) -> list[dict[str, int]]:
        log = self.work / "calls.jsonl"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]


def fake_store(tmp_path: Path, mode: str = "ok") -> FakeStore:
    work = tmp_path / "fake-weed"
    work.mkdir()
    weed = work / "weed"
    weed.write_text(FAKE_WEED)
    weed.chmod(0o755)
    return FakeStore(work=work, state=tmp_path / "state", mode=mode)


def allocate(count: str) -> subprocess.CompletedProcess[str]:
    """Run the script's port allocator exactly as `start` uses it."""
    return subprocess.run(
        ["bash", str(SCRIPT), "ports", count],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
