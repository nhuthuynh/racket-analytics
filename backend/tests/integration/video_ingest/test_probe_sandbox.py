"""The probe's process sandbox is enforced on a real child process (ST-009; NFR-054;
AQS/SEC-06 13.2.4, AQS/SEC-10).

Boundary crossed: the OS process boundary (fork/exec, rlimits, signals, pipes). Stand-in
"ffprobe" programs misbehave on purpose (hang, spin, allocate, write files, read secrets), and
the real ffprobe binary (``FFPROBE_BIN`` or ``ffprobe`` on PATH) probes the synthetic fixture over
HTTP under the default limits. Container-level isolation (network, read-only root, caps) is
IT-00-10.
"""

from __future__ import annotations

import functools
import http.server
import json
import shutil
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from racket.video_ingest.domain import MediaFacts
from racket.video_ingest.probe import ProbeFailed, ProbeLimits, ffprobe_bin, run_ffprobe
from tests.support.paths import SYNTHETIC_60S

URL = "http://127.0.0.1:9/racket-media/originals/x?X-Amz-Signature=deadbeefcafe"
FAST = ProbeLimits(wall_clock_s=5, cpu_s=5, memory_bytes=512 * 1024**2)


def fake_ffprobe(tmp_path: Path, body: str) -> str:
    """An executable stand-in that ignores its argv and runs ``body`` (Python)."""
    script = tmp_path / "fake-ffprobe"
    script.write_text(f"#!{sys.executable}\nimport json, os, sys, time\n{body}\n")
    script.chmod(0o755)
    return str(script)


# ------------------------------------------------------------------ negative cases first
def test_a_hanging_probe_is_killed_at_the_wall_clock_limit(tmp_path: Path) -> None:
    binary = fake_ffprobe(tmp_path, "time.sleep(60)")
    started = time.monotonic()

    with pytest.raises(ProbeFailed) as info:
        run_ffprobe(URL, binary=binary, limits=ProbeLimits(wall_clock_s=1, cpu_s=1))

    assert time.monotonic() - started < 5
    assert "deadbeefcafe" not in str(info.value)  # the presigned URL is a bearer secret


def test_a_cpu_spinning_probe_is_killed_at_the_cpu_limit(tmp_path: Path) -> None:
    binary = fake_ffprobe(tmp_path, "while True:\n    pass")
    started = time.monotonic()

    with pytest.raises(ProbeFailed):
        run_ffprobe(URL, binary=binary, limits=ProbeLimits(wall_clock_s=30, cpu_s=1))

    assert time.monotonic() - started < 10  # the CPU limit, not the wall clock, stopped it


def test_a_probe_cannot_allocate_beyond_the_memory_limit(tmp_path: Path) -> None:
    binary = fake_ffprobe(
        tmp_path,
        "try:\n"
        "    blob = bytearray(1024 * 1024**2)\n"
        "    print(json.dumps({'allocated': len(blob)}))\n"
        "except MemoryError:\n"
        "    sys.exit(1)",
    )

    with pytest.raises(ProbeFailed):
        run_ffprobe(URL, binary=binary, limits=FAST)


def test_a_probe_cannot_write_files(tmp_path: Path) -> None:
    target = tmp_path / "dropped.bin"
    binary = fake_ffprobe(
        tmp_path,
        f"with open({str(target)!r}, 'wb') as f:\n"
        "    f.write(b'x' * 4096)\n"
        "print(json.dumps({'wrote': True}))",
    )

    with pytest.raises(ProbeFailed):
        run_ffprobe(URL, binary=binary, limits=FAST)
    assert not target.exists() or target.stat().st_size == 0


def test_a_probe_cannot_open_many_files(tmp_path: Path) -> None:
    binary = fake_ffprobe(
        tmp_path,
        "handles = [open('/dev/null') for _ in range(256)]\nprint(json.dumps({'n': len(handles)}))",
    )

    with pytest.raises(ProbeFailed):
        run_ffprobe(URL, binary=binary, limits=FAST)


def test_a_probe_printing_without_end_is_cut_off(tmp_path: Path) -> None:
    binary = fake_ffprobe(tmp_path, "while True:\n    sys.stdout.write('[' * 65536)")
    started = time.monotonic()

    with pytest.raises(ProbeFailed):
        run_ffprobe(
            URL, binary=binary,
            limits=ProbeLimits(wall_clock_s=20, cpu_s=20, max_output_bytes=1024**2),
        )  # fmt: skip

    assert time.monotonic() - started < 10  # the output cap, not the wall clock, stopped it


def test_a_probe_sees_no_secrets_in_its_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "s3cr3t-value")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:db-pass@db/x")
    binary = fake_ffprobe(tmp_path, "print(json.dumps(dict(os.environ)))")

    seen = run_ffprobe(URL, binary=binary, limits=FAST)

    dumped = json.dumps(seen)
    assert "s3cr3t-value" not in dumped
    assert "db-pass" not in dumped
    assert set(seen) <= {"PATH", "LC_ALL"}


def test_a_probe_reading_stdin_gets_end_of_file(tmp_path: Path) -> None:
    binary = fake_ffprobe(tmp_path, "print(json.dumps({'stdin': sys.stdin.read()}))")

    assert run_ffprobe(URL, binary=binary, limits=FAST) == {"stdin": ""}


def test_a_probe_gets_only_the_fixed_argv(tmp_path: Path) -> None:
    binary = fake_ffprobe(tmp_path, "print(json.dumps(sys.argv[1:]))")

    argv = run_ffprobe(URL, binary=binary, limits=FAST)

    assert argv[-1] == URL
    assert "file" not in argv[argv.index("-protocol_whitelist") + 1].split(",")


# ------------------------------------------------------------------ the real binary
class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def fixture_server() -> Iterator[str]:
    handler = functools.partial(_QuietHandler, directory=str(SYNTHETIC_60S))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/clip.mp4"
    finally:
        server.shutdown()
        server.server_close()


def test_the_real_ffprobe_works_inside_the_default_limits(fixture_server: str) -> None:
    if shutil.which(ffprobe_bin()) is None:
        pytest.fail(f"ffprobe binary not found: {ffprobe_bin()}", pytrace=False)

    facts = MediaFacts.from_ffprobe(run_ffprobe(fixture_server))

    assert (facts.duration_ms, facts.fps, facts.width, facts.height) == (60000, 60, 1920, 1080)
    assert facts.has_audio is True
