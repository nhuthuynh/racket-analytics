"""CI-OBJSTORE-INIT-HANG: the objectstore-init one-shot is bounded in time.

Run 38096146829 (job 114347835595): `weed shell` started before the master listed the filer
and never returned, so `compose up --wait` hung until the 45-minute job timeout. The one-shot's
own command from infra/compose.yaml runs here under /bin/sh against a stand-in `weed` that
hangs on chosen calls, with the retry count and per-call limit made small through the
command's own shell defaults.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import time
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

COMPOSE = REPO_ROOT / "infra" / "compose.yaml"
BUCKET = "racket-media"
BOUND_S = 30

FAKE_WEED = """#!/bin/sh
n=$(cat "$WEED_STATE" 2>/dev/null || echo 0); n=$((n + 1)); echo "$n" > "$WEED_STATE"
cmd=$(cat)
if [ "$n" -le "$WEED_HANG_CALLS" ]; then exec sleep 1000; fi
case "$cmd" in *s3.bucket.list*) printf '  %s\\tsize:0\\n' "$S3_BUCKET_MEDIA";; *) echo ok;; esac
"""


def init_command() -> str:
    svc = yaml.safe_load(COMPOSE.read_text())["services"]["objectstore-init"]
    command = svc["command"]
    script = command[0] if isinstance(command, list) else command
    return script.replace("$$", "$")  # Compose's escape for a literal "$"


def run_init(tmp_path: Path, hang_calls: int) -> tuple[subprocess.CompletedProcess[str], float]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    weed = bin_dir / "weed"
    weed.write_text(FAKE_WEED)
    weed.chmod(weed.stat().st_mode | stat.S_IEXEC)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "S3_BUCKET_MEDIA": BUCKET,
        "WEED_STATE": str(tmp_path / "calls"),
        "WEED_HANG_CALLS": str(hang_calls),
        "OBJSTORE_INIT_TRIES": "3",
        "OBJSTORE_INIT_SHELL_TIMEOUT_S": "1",
    }
    start = time.monotonic()
    try:
        res = subprocess.run(
            ["/bin/sh", "-c", init_command()],
            capture_output=True,
            text=True,
            env=env,
            timeout=BOUND_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"objectstore-init still running after {BOUND_S}s: a stuck shell hangs it")
    return res, time.monotonic() - start


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_every_weed_shell_call_has_a_time_limit() -> None:
    calls = re.findall(r"(\S+\s+\S+\s+)weed shell", init_command())
    assert calls, "objectstore-init no longer runs `weed shell`"
    for prefix in calls:
        assert prefix.split()[0] == "timeout", f"`weed shell` without `timeout`: {prefix!r}"


@pytest.mark.unit
def test_the_retry_count_and_shell_limit_have_bounded_defaults() -> None:
    script = init_command()
    tries = re.search(r"\$\{OBJSTORE_INIT_TRIES:-(\d+)\}", script)
    limit = re.search(r"\$\{OBJSTORE_INIT_SHELL_TIMEOUT_S:-(\d+)\}", script)
    assert tries, "objectstore-init needs a bounded default retry count"
    assert limit, "objectstore-init needs a bounded default per-call time limit"
    # Two shell calls per try plus a 1 s pause: the worst case stays far below the E2E job's
    # 45-minute timeout, so a stuck store fails `up --wait` with its own message.
    assert int(tries.group(1)) * (2 * int(limit.group(1)) + 1) <= 600


@pytest.mark.integration
def test_a_shell_that_never_answers_fails_within_the_bound(tmp_path: Path) -> None:
    res, elapsed = run_init(tmp_path, hang_calls=10_000)
    assert res.returncode != 0
    assert BUCKET in res.stderr
    assert elapsed < BOUND_S


@pytest.mark.integration
def test_a_shell_that_hangs_once_then_answers_creates_the_bucket(tmp_path: Path) -> None:
    res, _ = run_init(tmp_path, hang_calls=1)
    assert res.returncode == 0, res.stdout + res.stderr
