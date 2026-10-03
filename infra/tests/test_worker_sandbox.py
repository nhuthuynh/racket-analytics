"""ST-009 (NFR-054; AQS/SEC-06 13.2.4, AQS/SEC-10): the worker container is a sandbox.

Static checks of infra/compose.yaml and the worker image recipe. The live check (a public host is
unreachable from the running worker, the object store is reachable) is backend IT-00-10. The
per-process limits on ffprobe are backend tests/integration/video_ingest/test_probe_sandbox.py.
Owner: senior-ml-cv-engineer (added alongside the SRE's tests in test_compose.py).
"""

from __future__ import annotations

import re

import pytest
import yaml
from conftest import REPO_ROOT

COMPOSE = REPO_ROOT / "infra" / "compose.yaml"
DOCKERFILE = REPO_ROOT / "infra" / "docker" / "backend.Dockerfile"


def worker() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]["worker"]


def worker_stage() -> str:
    text = DOCKERFILE.read_text()
    return text[text.index("FROM base AS worker") :]


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_worker_image_does_not_install_a_distro_ffmpeg() -> None:
    # Debian/Ubuntu ffmpeg packages are GPL-enabled builds; ADR 0008 requires LGPL.
    assert not re.search(r"apt-get install[^\n]*\bffmpeg\b", DOCKERFILE.read_text())


@pytest.mark.unit
def test_ffprobe_build_is_pinned_and_checksummed() -> None:
    text = DOCKERFILE.read_text()
    assert re.search(r"ARG FFMPEG_BUILD_TAG=autobuild-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}\b", text)
    assert "latest" not in re.search(r"ARG FFMPEG_BUILD_NAME=(\S+)", text).group(1)  # type: ignore[union-attr]
    assert re.search(r"ARG FFMPEG_BUILD_SHA256=[0-9a-f]{64}\b", text)
    assert "-lgpl" in re.search(r"ARG FFMPEG_BUILD_NAME=(\S+)", text).group(1)  # type: ignore[union-attr]


@pytest.mark.unit
def test_image_build_refuses_a_gpl_or_nonfree_ffprobe() -> None:
    text = DOCKERFILE.read_text()
    assert "--enable-gpl" in text
    assert "--enable-nonfree" in text
    assert "refusing a GPL or nonfree ffprobe build" in text


@pytest.mark.unit
def test_worker_has_a_process_count_limit() -> None:
    # RLIMIT_NPROC does not bind root; the container pid limit does (fork bombs, NFR-054).
    limit = worker()["deploy"]["resources"]["limits"].get("pids")
    assert isinstance(limit, int)
    assert 0 < limit <= 512


@pytest.mark.unit
def test_worker_has_cpu_and_memory_limits() -> None:
    limits = worker()["deploy"]["resources"]["limits"]
    assert float(limits["cpus"]) > 0
    assert str(limits["memory"]).lower().endswith(("m", "g"))


@pytest.mark.unit
def test_worker_is_hardened() -> None:
    svc = worker()
    assert svc.get("read_only") is True
    assert "ALL" in svc.get("cap_drop", [])
    assert "no-new-privileges:true" in svc.get("security_opt", [])
    assert not svc.get("ports")
    assert not svc.get("privileged")


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_worker_runs_as_non_root_with_the_pinned_ffprobe() -> None:
    stage = worker_stage()
    assert re.search(r"^USER app$", stage, re.MULTILINE)
    assert "FFPROBE_BIN=/opt/ffmpeg/bin/ffprobe" in stage
    assert "COPY --from=ffprobe /out /opt/ffmpeg" in stage
