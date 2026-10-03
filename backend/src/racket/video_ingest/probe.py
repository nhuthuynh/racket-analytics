"""The ``probe`` stage: ffprobe a stored original and record its ``MediaFacts`` (ST-009 stage 0;
owned by Capture & Media, run by the job runtime, context map R7).

* ffprobe reads the object through a presigned GET (TTL <= 15 min, NFR-055). The URL is a
  bearer secret: it is never logged, and ffprobe's stderr (which can echo it) is discarded.
* No user-supplied name reaches the tool: the only argument is the server-generated URL
  (NFR-054; AQS/SEC-06 13.2.4).
* ffprobe parses untrusted media, so it runs in a process sandbox (``run_ffprobe``, ADR 0020):
  http(s) URLs only, no ``file`` protocol, scrubbed environment, rlimits on CPU, memory, files
  and processes, a wall-clock deadline and an output cap. The container adds the network
  sandbox (Compose ``worker`` on an internal network).
* Fault injection (ADR 0012) is honoured only when ``APP_ENV=test`` (``Settings`` drops it
  otherwise).
"""

from __future__ import annotations

import json
import logging
import os
import selectors
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from racket.analysis_jobs.stage import StageContext
from racket.video_ingest.domain import MediaFacts
from racket.video_ingest.repository import PROBE_DONE, PROBE_FAILED, MediaRepository

log = logging.getLogger(__name__)
PRESIGN_TTL_S = 15 * 60


class ProbeFailed(RuntimeError):
    pass


class InjectedFault(RuntimeError):
    pass


def ffprobe_bin() -> str:
    return os.environ.get("FFPROBE_BIN", "ffprobe")


def ffprobe_version() -> str:
    try:
        out = subprocess.run(  # noqa: S603 - fixed argv, no user input
            [ffprobe_bin(), "-version"],
            capture_output=True, text=True, timeout=10, check=False,
            stdin=subprocess.DEVNULL, env=child_environment(os.environ),
        )  # fmt: skip
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    return out.stdout.splitlines()[0] if out.stdout else "unavailable"


# ------------------------------------------------------------------ process sandbox (NFR-054)
_ALLOWED_SCHEMES = ("http", "https")
_PROTOCOL_WHITELIST = "http,https,tcp,tls"  # never "file", "concat", "subfile", ...
# Input formats ffprobe may demux: the MP4/MOV family only (SEC-R1-01; threat model T-WS-2).
# Without it, auto-detection lets a DASH/HLS manifest uploaded as a "video" make the worker
# fetch any URL the uploader chooses (SSRF), even under the protocol whitelist.
_FORMAT_WHITELIST = "mov,mp4,m4a,3gp,3g2,mj2"
_CHILD_ENV_KEYS = ("PATH",)


@dataclass(frozen=True)
class ProbeLimits:
    """Per-process limits for one ffprobe run, inside the container's own limits (Compose
    ``worker``: 2 CPU, 2 GB, pids). ``processes`` (RLIMIT_NPROC) does not bind root; the
    container's ``pids_limit`` does."""

    wall_clock_s: float = 120
    cpu_s: int = 60
    memory_bytes: int = 1024**3
    open_files: int = 64
    processes: int = 256
    max_output_bytes: int = 4 * 1024**2
    file_size_bytes: int = 0

    def __post_init__(self) -> None:
        for name in ("wall_clock_s", "cpu_s", "memory_bytes", "open_files", "processes",
                     "max_output_bytes"):  # fmt: skip
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.file_size_bytes < 0:
            raise ValueError("file_size_bytes must not be negative")


def ffprobe_argv(binary: str, url: str) -> list[str]:
    """The complete argv: fixed flags and the server-generated presigned URL, nothing else.

    Refuses anything but an ``http(s)://host/...`` URL, so no local path or ffmpeg pseudo
    protocol (``file:``, ``concat:``, ``subfile,...``) can reach the tool even by mistake. The
    refusal never echoes the URL (it is a bearer secret, NFR-055)."""
    parts = urlsplit(url)
    if parts.scheme not in _ALLOWED_SCHEMES or not parts.hostname:
        raise ProbeFailed("refused: the probe reads only http(s) object-store URLs")
    return [
        binary,
        "-v", "error",
        "-protocol_whitelist", _PROTOCOL_WHITELIST,
        "-format_whitelist", _FORMAT_WHITELIST,
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        url,
    ]  # fmt: skip


def child_environment(parent: Mapping[str, str]) -> dict[str, str]:
    """ffprobe gets PATH and a fixed locale only: no DB URL, S3 keys or proxy settings."""
    env = {key: parent[key] for key in _CHILD_ENV_KEYS if key in parent}
    env["LC_ALL"] = "C"
    return env


# Runs in the child between fork and the tool: sets rlimits, restores the signals Python
# ignores (so SIGXFSZ/SIGPIPE terminate the tool), then execs it. A separate interpreter instead
# of ``preexec_fn``, which is unsafe while the lease heartbeat thread runs.
_LAUNCHER = """
import os, resource as r, signal, sys
def cap(res, value):
    hard = r.getrlimit(res)[1]
    value = value if hard == r.RLIM_INFINITY else min(value, hard)
    r.setrlimit(res, (value, value))
cpu, mem, nofile, nproc, fsize = (int(v) for v in sys.argv[1:6])
cap(r.RLIMIT_AS, mem)
cap(r.RLIMIT_NOFILE, nofile)
cap(r.RLIMIT_NPROC, nproc)
cap(r.RLIMIT_FSIZE, fsize)
cap(r.RLIMIT_CORE, 0)
hard = r.getrlimit(r.RLIMIT_CPU)[1]
r.setrlimit(r.RLIMIT_CPU, (cpu, cpu + 1 if hard == r.RLIM_INFINITY else min(cpu + 1, hard)))
for sig in (signal.SIGPIPE, signal.SIGXFSZ):
    signal.signal(sig, signal.SIG_DFL)
os.execv(sys.argv[7], sys.argv[7:])
"""


def _sandboxed(argv: list[str], limits: ProbeLimits) -> list[str]:
    caps = (limits.cpu_s, limits.memory_bytes, limits.open_files, limits.processes,
            limits.file_size_bytes)  # fmt: skip
    return [sys.executable, "-I", "-S", "-c", _LAUNCHER, *map(str, caps), "--", *argv]


def _read_capped(proc: subprocess.Popen[bytes], limits: ProbeLimits) -> bytes:
    if proc.stdout is None:  # pragma: no cover - Popen(stdout=PIPE) always sets it
        raise ProbeFailed("ffprobe has no output pipe")
    deadline = time.monotonic() + limits.wall_clock_s
    chunks: list[bytes] = []
    size = 0
    with selectors.DefaultSelector() as sel:
        sel.register(proc.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProbeFailed(f"ffprobe exceeded the {limits.wall_clock_s:g} s wall clock")
            if not sel.select(timeout=remaining):
                continue
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                break
            size += len(chunk)
            if size > limits.max_output_bytes:
                raise ProbeFailed("ffprobe printed more than the output limit")
            chunks.append(chunk)
    try:
        proc.wait(timeout=max(0.1, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        raise ProbeFailed(f"ffprobe exceeded the {limits.wall_clock_s:g} s wall clock") from None
    return b"".join(chunks)


def run_ffprobe(url: str, *, binary: str | None = None,
                limits: ProbeLimits | None = None) -> Any:  # fmt: skip
    """Run ffprobe on ``url`` in a process sandbox and return its parsed JSON.

    Sandbox: fixed argv (``ffprobe_argv``), stdin ``/dev/null``, stderr discarded (it can echo
    the URL), a scrubbed environment, rlimits on CPU, memory, open files, processes and file
    writes, a wall-clock deadline and an output cap. Any breach kills the process and raises
    ``ProbeFailed`` without the URL in its message."""
    limits = limits or ProbeLimits()
    env = child_environment(os.environ)
    resolved = shutil.which(binary or ffprobe_bin(), path=env.get("PATH"))
    if resolved is None:
        raise ProbeFailed("ffprobe binary not found")
    argv = _sandboxed(ffprobe_argv(resolved, url), limits)
    try:
        proc = subprocess.Popen(  # noqa: S603 - fixed argv; the URL is server-generated
            argv,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=env, cwd="/", close_fds=True,
            start_new_session=True,
        )  # fmt: skip
    except OSError:
        raise ProbeFailed("ffprobe could not be started") from None
    try:
        out = _read_capped(proc, limits)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if proc.stdout is not None:
            proc.stdout.close()
    if proc.returncode != 0:
        raise ProbeFailed(f"ffprobe exited with {proc.returncode}")
    try:
        return json.loads(out)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ProbeFailed("ffprobe printed no JSON") from None


class ProbeStage:
    name = "probe"
    failure_reason = "probe_failed"

    def run(self, ctx: StageContext) -> None:
        media = MediaRepository(ctx.session)
        match_id = ctx.key.match_id
        asset = media.asset_for_match(match_id)
        if asset is None:
            raise ProbeFailed("no media asset for this match")

        fault = ctx.settings.fault_injection
        if fault.startswith("probe:sleep="):
            time.sleep(float(fault.partition("=")[2]))
        if fault == "probe:fail_after_partial_write":
            media.write_partial_facts(asset.id, match_id, container="partial")
            raise InjectedFault("injected after a partial write")

        url = ctx.store().presigned_get(asset.object_key, PRESIGN_TTL_S)
        facts = MediaFacts.from_ffprobe(run_ffprobe(url))
        media.save_facts(asset.id, match_id, facts)
        media.set_probe_status(asset.id, PROBE_DONE)
        log.info("probe done", extra={"event": "probe.done", "media_asset_id": str(asset.id)})

    def on_failure(self, ctx: StageContext) -> None:
        media = MediaRepository(ctx.session)
        asset = media.asset_for_match(ctx.key.match_id)
        if asset is not None:
            media.set_probe_status(asset.id, PROBE_FAILED)
