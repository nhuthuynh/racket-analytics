#!/usr/bin/env python3
"""Fast, bounded ffmpeg/ffprobe install for CI (CI-FFMPEG; NFR-073; NFR-062).

CI run 42019671445 (PR #225): `apt-get install ffmpeg` fetched 62.8 MB at 58.9 kB/s and took
17 m 48 s of a 20 min job. This installs the pinned BtbN LGPL build that the worker image ships
(scripts/ci/ffmpeg-pin.json = infra/docker/backend.Dockerfile ARGs) into --dest instead:

1. Cache hit: every pinned file in --dest (restored by actions/cache) matches its pinned SHA-256.
   No network.
2. Otherwise: discard the pinned files in --dest, download the archive (at most --attempts
   attempts, each under --attempt-timeout, cycling over the pin's sources, all inside --budget),
   verify its SHA-256, extract only the pinned files and verify each one. Nothing unverified is
   left in --dest.
3. Append --dest/bin to --github-path ($GITHUB_PATH).

Usage: install_ffmpeg.py --pin scripts/ci/ffmpeg-pin.json --dest ~/.cache/racket-ffmpeg
           [--attempts 2] [--attempt-timeout 75] [--budget 180] [--github-path "$GITHUB_PATH"]
Exit codes: 0 installed; 1 checksum or archive check failed (fails closed); 2 usage or pin
error; 3 every attempt failed or the budget ran out (named "CI-FFMPEG: ... exceeded its budget").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tarfile
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

DEFAULT_ATTEMPTS = 2
DEFAULT_ATTEMPT_TIMEOUT_S = 75.0
DEFAULT_BUDGET_S = 180.0
SCHEMA = "ffmpeg-pin/v1"
CHUNK = 1 << 20
_SHA = re.compile(r"^[0-9a-f]{64}$")


class PinError(Exception):
    """The pin file is missing, malformed or unsafe."""


class VerifyError(Exception):
    """A checksum or archive check failed: fail closed."""


class AttemptTimeout(Exception):
    """One download attempt ran past its deadline."""


@dataclass(frozen=True)
class Pin:
    tag: str
    name: str
    archive_sha256: str
    sources: tuple[str, ...]
    files: dict[str, str]


def load_pin(path: Path) -> Pin:
    try:
        raw: dict[str, Any] = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise PinError(f"cannot read pin {path}: {exc}") from exc
    if raw.get("schema") != SCHEMA:
        raise PinError(f"pin schema is {raw.get('schema')!r}, expected {SCHEMA!r}")
    tag, name, sha = raw.get("tag"), raw.get("name"), raw.get("archive_sha256")
    sources, files = raw.get("sources"), raw.get("files")
    if not (isinstance(tag, str) and tag and isinstance(name, str) and name):
        raise PinError("pin needs a tag and a name")
    if not (isinstance(sha, str) and _SHA.match(sha)):
        raise PinError("archive_sha256 is not a lowercase SHA-256")
    if not (isinstance(sources, list) and sources and all(isinstance(s, str) for s in sources)):
        raise PinError("pin needs at least one source")
    if not (isinstance(files, dict) and files):
        raise PinError("pin needs at least one file")
    for rel, digest in files.items():
        parts = PurePosixPath(rel).parts
        if PurePosixPath(rel).is_absolute() or ".." in parts or not parts:
            raise PinError(f"unsafe file path in pin: {rel!r}")
        if not (isinstance(digest, str) and _SHA.match(digest)):
            raise PinError(f"{rel}: not a lowercase SHA-256")
    return Pin(tag, name, sha, tuple(sources), dict(files))


def source_for(pin: Pin, attempt: int) -> str:
    return pin.sources[attempt % len(pin.sources)].format(tag=pin.tag, name=pin.name)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def cache_state(dest: Path, files: dict[str, str]) -> tuple[str, str]:
    """('hit'|'miss'|'mismatch', detail) for the pinned files in dest."""
    present = [rel for rel in files if (dest / rel).is_file()]
    if not present:
        return "miss", "no cached build"
    for rel, want in files.items():
        path = dest / rel
        if not path.is_file():
            return "mismatch", f"{rel} missing"
        if file_sha256(path) != want:
            return "mismatch", f"{rel} sha256 differs from the pin"
    return "hit", f"{len(files)} files verified"


def discard(dest: Path, files: dict[str, str]) -> None:
    for rel in files:
        for path in (dest / rel, dest / f"{rel}.part"):
            path.unlink(missing_ok=True)


def download(
    url: str,
    out: Path,
    deadline: float,
    opener: Callable[..., Any] = urllib.request.urlopen,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Stream url to out; raise AttemptTimeout once clock() passes deadline (a trickling
    transfer, as in run 42019671445, never trips a socket timeout on its own)."""
    remaining = deadline - clock()
    if remaining <= 0:
        raise AttemptTimeout("no time left")
    with opener(url, timeout=max(0.5, min(remaining, 10.0))) as resp, out.open("wb") as f:
        # read1 returns what has arrived; read(n) would block until n bytes on a trickle.
        read = getattr(resp, "read1", resp.read)
        while True:
            if clock() > deadline:
                raise AttemptTimeout("deadline passed")
            chunk = read(CHUNK)
            if not chunk:
                return
            f.write(chunk)


def verify_archive(path: Path, want: str) -> None:
    got = file_sha256(path)
    if got != want:
        raise VerifyError(f"sha256 mismatch for the archive: got {got}, pinned {want}")


def extract(archive: Path, name: str, files: dict[str, str], dest: Path) -> None:
    """Extract only the pinned files, verify each; on any failure nothing pinned is left."""
    wanted = {f"{name}/{rel}": rel for rel in files}
    done: set[str] = set()
    try:
        with tarfile.open(archive, mode="r|xz") as tar:
            for member in tar:
                rel = wanted.get(member.name)
                if rel is None or not member.isfile():
                    continue
                src = tar.extractfile(member)
                if src is None:
                    continue
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                part = target.with_name(target.name + ".part")
                digest = hashlib.sha256()
                with part.open("wb") as f:
                    while chunk := src.read(CHUNK):
                        digest.update(chunk)
                        f.write(chunk)
                if digest.hexdigest() != files[rel]:
                    raise VerifyError(f"sha256 mismatch for {rel}: got {digest.hexdigest()}")
                part.chmod(0o755 if rel.startswith("bin/") else 0o644)
                part.replace(target)
                done.add(rel)
        missing = sorted(set(files) - done)
        if missing:
            raise VerifyError(f"archive has no {', '.join(missing)} under {name}/")
    except (tarfile.TarError, EOFError, OSError) as exc:
        discard(dest, files)
        raise VerifyError(f"cannot read the archive: {exc}") from exc
    except VerifyError:
        discard(dest, files)
        raise


def budget_message(budget: float, attempts: list[str]) -> str:
    tried = "; ".join(f"attempt {i + 1}: {a}" for i, a in enumerate(attempts)) or "no attempt"
    return (
        f"CI-FFMPEG: ffmpeg install exceeded its budget of {budget:g} s after {len(attempts)} "
        f"attempts ({tried}). The ffmpeg-dependent suites cannot run; re-run the job, or add a "
        "mirror serving the same archive to scripts/ci/ffmpeg-pin.json (it is SHA-256 verified)."
    )


def fetch(pin: Pin, dest: Path, args: argparse.Namespace, started: float) -> int:
    attempts: list[str] = []
    archive = dest.parent / f".{pin.name}.tar.xz"
    dest.mkdir(parents=True, exist_ok=True)
    try:
        for i in range(args.attempts):
            url = source_for(pin, i)
            host = urllib.parse.urlsplit(url).netloc
            t0 = time.monotonic()
            deadline = min(t0 + args.attempt_timeout, started + args.budget)
            if t0 >= started + args.budget:
                break
            try:
                download(url, archive, deadline)
            except AttemptTimeout:
                attempts.append(f"{host}: timed out after {time.monotonic() - t0:.0f} s")
                print(f"CI-FFMPEG: attempt {i + 1} {attempts[-1]}", flush=True)
                continue
            except OSError as exc:
                attempts.append(f"{host}: {exc}")
                print(f"CI-FFMPEG: attempt {i + 1} failed: {exc}", flush=True)
                continue
            verify_archive(archive, pin.archive_sha256)
            extract(archive, pin.name, pin.files, dest)
            print(
                f"CI-FFMPEG: attempt {i + 1} downloaded {pin.name} from {host} in "
                f"{time.monotonic() - t0:.1f} s; archive and {len(pin.files)} files verified",
                flush=True,
            )
            return 0
    finally:
        archive.unlink(missing_ok=True)
    print(budget_message(args.budget, attempts), file=sys.stderr, flush=True)
    return 3


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--pin", type=Path, required=True)
    ap.add_argument("--dest", type=Path, required=True)
    ap.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    ap.add_argument("--attempt-timeout", type=float, default=DEFAULT_ATTEMPT_TIMEOUT_S)
    ap.add_argument("--budget", type=float, default=DEFAULT_BUDGET_S)
    ap.add_argument("--github-path", type=Path, default=None)
    args = ap.parse_args(argv)
    started = time.monotonic()
    try:
        pin = load_pin(args.pin)
    except PinError as exc:
        print(f"CI-FFMPEG: {exc}", file=sys.stderr)
        return 2
    if args.attempts < 1 or args.attempt_timeout <= 0 or args.budget <= 0:
        print("CI-FFMPEG: attempts, attempt timeout and budget must be > 0", file=sys.stderr)
        return 2
    dest = args.dest.expanduser().resolve()
    state, detail = cache_state(dest, pin.files)
    if state == "hit":
        print(f"CI-FFMPEG: cache hit, {detail} in {time.monotonic() - started:.1f} s", flush=True)
    else:
        if state == "mismatch":
            print(f"CI-FFMPEG: {detail}; discarding the cache", flush=True)
            discard(dest, pin.files)
        try:
            code = fetch(pin, dest, args, started)
        except VerifyError as exc:
            print(f"CI-FFMPEG: {exc}; refusing the build (fails closed)", file=sys.stderr)
            return 1
        if code:
            return code
    if args.github_path is not None:
        with args.github_path.open("a") as f:
            f.write(f"{dest / 'bin'}{os.linesep}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
