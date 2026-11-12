"""Binds tests/features/ci_ffmpeg_install.feature (CI-FFMPEG; story "CI first"; ST-002).

The workflow rules read the real ci.yml and the real composite action; the install scenarios
run the real scripts/ci/install_ffmpeg.py as a subprocess against a local HTTP source.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR
from ffmpeg_fixtures import FILES, Source, fill_install_dir, serve, sha256, write_pin
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("ci_ffmpeg_install.feature")

CI = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
ACTION_DIR = REPO_ROOT / ".github" / "actions" / "install-ffmpeg"
SHARED = "./.github/actions/install-ffmpeg"
SCRIPT = SCRIPTS_DIR / "ci" / "install_ffmpeg.py"
PIN = SCRIPTS_DIR / "ci" / "ffmpeg-pin.json"
DOCKERFILE = REPO_ROOT / "infra" / "docker" / "backend.Dockerfile"


def ffmpeg_steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        s
        for s in job["steps"]
        if "ffmpeg" in (s.get("run", "") + s.get("uses", "") + s.get("name", "")).lower()
        or "ffprobe" in s.get("name", "").lower()
    ]


# ------------------------------------------------------------------ workflow rules
@then(
    parsers.parse(
        'the jobs "{a}", "{b}" and "{c}" install ffmpeg only through the shared install action'
    )
)
def shared_only(a: str, b: str, c: str) -> None:
    for name in (a, b, c):
        steps = ffmpeg_steps(CI["jobs"][name])
        installs = [s for s in steps if s.get("uses") == SHARED]
        assert len(installs) == 1, f"{name}: {len(installs)} shared install steps ({steps})"
    assert (ACTION_DIR / "action.yml").is_file()


@then("no CI job installs ffmpeg with apt")
def no_apt() -> None:
    for name, job in CI["jobs"].items():
        for s in job["steps"]:
            run = s.get("run", "")
            assert not re.search(r"apt-get install[^\n]*\bffmpeg\b", run), f"{name}: {run}"


@then("every shared install step has a time limit of at most 4 minutes")
def bounded_steps() -> None:
    seen = 0
    for name, job in CI["jobs"].items():
        for s in job["steps"]:
            if s.get("uses") == SHARED:
                seen += 1
                assert 0 < int(s.get("timeout-minutes", 0)) <= 4, f"{name}: {s}"
    assert seen >= 3


@then("the build pinned for CI is the ffprobe build the backend Dockerfile pins")
def same_build() -> None:
    pin = json.loads(PIN.read_text())
    docker = dict(re.findall(r"^ARG (FFMPEG_BUILD_\w+)=(\S+)$", DOCKERFILE.read_text(), re.M))
    assert pin["tag"] == docker["FFMPEG_BUILD_TAG"]
    assert pin["name"] == docker["FFMPEG_BUILD_NAME"]
    assert pin["archive_sha256"] == docker["FFMPEG_BUILD_SHA256"]
    assert "-lgpl-" in pin["name"]


# ------------------------------------------------------------------ install scenarios
@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    gh_path = tmp_path / "github_path"
    gh_path.write_text("")
    return {
        "tmp": tmp_path,
        "dest": tmp_path / "cache" / "racket-ffmpeg",
        "github_path": gh_path,
        "sources": {"a": Source(), "b": Source()},
        "attempt_timeout": "60",
    }


@given("the pinned build is already in the install directory")
def cached(ctx: dict[str, Any]) -> None:
    fill_install_dir(ctx["dest"])


@given("the cached ffprobe was changed")
def tampered(ctx: dict[str, Any]) -> None:
    (ctx["dest"] / "bin" / "ffprobe").write_bytes(b"#!/bin/sh\necho evil\n")


@given("the source serves an archive whose SHA-256 differs from the pin")
def other_bytes(ctx: dict[str, Any]) -> None:
    ctx["sources"]["a"].mode = "other"
    ctx["sources"]["b"].mode = "other"


@given("the first source stalls and the second source serves the pinned build")
def first_stalls(ctx: dict[str, Any]) -> None:
    ctx["sources"]["a"].mode = "stall"


@given("every source stalls")
def all_stall(ctx: dict[str, Any]) -> None:
    ctx["sources"]["a"].mode = "stall"
    ctx["sources"]["b"].mode = "stall"


def run_install(ctx: dict[str, Any]) -> None:
    with serve(ctx["sources"]) as base:
        pin = write_pin(
            ctx["tmp"] / "pin.json",
            [f"{base}/a/{{tag}}/{{name}}.tar.xz", f"{base}/b/{{tag}}/{{name}}.tar.xz"],
        )
        started = time.monotonic()
        ctx["res"] = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--pin",
                str(pin),
                "--dest",
                str(ctx["dest"]),
                "--attempt-timeout",
                ctx["attempt_timeout"],
                "--budget",
                "120",
                "--github-path",
                str(ctx["github_path"]),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            env={k: v for k, v in os.environ.items() if k != "GITHUB_PATH"},
        )
        ctx["elapsed"] = time.monotonic() - started


@when("the install runs")
def install(ctx: dict[str, Any]) -> None:
    run_install(ctx)


@when("the install runs with a 1 second limit per attempt")
def install_short(ctx: dict[str, Any]) -> None:
    ctx["attempt_timeout"] = "1"
    run_install(ctx)


def output(ctx: dict[str, Any]) -> str:
    return ctx["res"].stdout + ctx["res"].stderr


@then(parsers.parse('it succeeds reporting "{text}"'))
def succeeds(ctx: dict[str, Any], text: str) -> None:
    assert ctx["res"].returncode == 0, output(ctx)
    assert text in output(ctx), output(ctx)


@then("it downloaded nothing")
def nothing_downloaded(ctx: dict[str, Any]) -> None:
    assert [r for s in ctx["sources"].values() for r in s.requests] == []


@then("it took less than 60 seconds")
def fast(ctx: dict[str, Any]) -> None:
    assert ctx["elapsed"] < 60, ctx["elapsed"]


@then("the install directory's bin is added to the job's PATH")
def on_path(ctx: dict[str, Any]) -> None:
    lines = ctx["github_path"].read_text().splitlines()
    assert lines == [str(ctx["dest"] / "bin")]


@then("it downloaded the archive once")
def downloaded_once(ctx: dict[str, Any]) -> None:
    assert sum(len(s.requests) for s in ctx["sources"].values()) == 1


@then("the cached ffprobe matches its pinned checksum")
def ffprobe_ok(ctx: dict[str, Any]) -> None:
    data = (ctx["dest"] / "bin" / "ffprobe").read_bytes()
    assert sha256(data) == sha256(FILES["bin/ffprobe"])
    assert os.access(ctx["dest"] / "bin" / "ffprobe", os.X_OK)


@then(parsers.parse('it fails with exit code {code:d} naming "{text}"'))
def fails(ctx: dict[str, Any], code: int, text: str) -> None:
    assert ctx["res"].returncode == code, output(ctx)
    assert text in output(ctx), output(ctx)


@then("no ffmpeg or ffprobe is left in the install directory")
def nothing_left(ctx: dict[str, Any]) -> None:
    for rel in ("bin/ffmpeg", "bin/ffprobe"):
        assert not (ctx["dest"] / rel).exists(), rel
    assert ctx["github_path"].read_text() == ""


@then("each source was asked once")
def each_once(ctx: dict[str, Any]) -> None:
    assert [len(s.requests) for s in ctx["sources"].values()] == [1, 1]


@then(parsers.parse("it stopped within {seconds:d} seconds after {n:d} attempts"))
def stopped(ctx: dict[str, Any], seconds: int, n: int) -> None:
    assert ctx["elapsed"] < seconds, ctx["elapsed"]
    assert sum(len(s.requests) for s in ctx["sources"].values()) == n
    assert f"{n} attempts" in output(ctx), output(ctx)
