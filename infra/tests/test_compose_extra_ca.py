"""IT-04-14 and unit tests for C4-CA (VR3-S3-01): the optional ``extra_ca`` build secret.

Behind a TLS-intercepting proxy, ``EXTRA_CA_FILE=/path/ca.crt make up`` hands the proxy's CA to
every built service as the BuildKit secret ``extra_ca``; the Dockerfiles use it only inside
``RUN --mount=type=secret,id=extra_ca,required=false``, so it never lands in a layer. Unset (the
default), the build secret id is ``extra_ca_file``, which no Dockerfile mounts: the default build
runs exactly the steps it ran before. Negative cases first.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from extra_ca_fixtures import (
    COMPOSE,
    SECRET_ID,
    env_file,
    holds_certificate,
    make_ca,
    probe_build,
    render,
    rendered_secret_ids,
    sha256,
)

needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI missing")
SOURCE = "extra_ca_file"
TARGET = "${EXTRA_CA_FILE:+extra_ca}"
DOCKERFILES = sorted((REPO_ROOT / "infra" / "docker").glob("*.Dockerfile"))


def built() -> dict[str, dict]:
    services = yaml.safe_load(COMPOSE.read_text())["services"]
    return {n: s["build"] for n, s in services.items() if "build" in s}


def _secrets(build: dict) -> list[dict]:
    return [s if isinstance(s, dict) else {"source": s} for s in build.get("secrets") or []]


# ---------------------------------------------------------------- unit: negative cases first
@pytest.mark.unit
def test_no_build_service_hands_buildkit_extra_ca_unconditionally() -> None:
    """Default off: an `extra_ca` id that does not depend on EXTRA_CA_FILE would mount always."""
    offenders = [
        n
        for n, b in built().items()
        for s in _secrets(b)
        if (s.get("target") or s["source"]) == SECRET_ID
    ]
    assert offenders == []


@pytest.mark.unit
def test_no_build_service_lacks_the_optional_extra_ca_secret() -> None:
    offenders = [
        n for n, b in built().items() if {"source": SOURCE, "target": TARGET} not in _secrets(b)
    ]
    assert built()
    assert offenders == [], f"no optional extra_ca build secret: {offenders}"


@pytest.mark.unit
@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=lambda p: p.name)
def test_no_dockerfile_requires_extra_ca_or_copies_it_into_a_layer(dockerfile: Path) -> None:
    text = dockerfile.read_text()
    mounts = re.findall(r"--mount=type=secret,id=extra_ca\S*", text)
    assert mounts, "the Dockerfile never mounts extra_ca"
    assert all(m == "--mount=type=secret,id=extra_ca,required=false" for m in mounts), mounts
    for line in text.splitlines():
        if "/run/secrets/extra_ca" in line:
            assert not re.search(r"\b(cp|mv|cat|tee|install)\b|>|^\s*(COPY|ADD)\b", line), line


# ---------------------------------------------------------------- unit: positive cases
@pytest.mark.unit
def test_the_secret_reads_extra_ca_file_and_defaults_to_an_empty_unmounted_source() -> None:
    top = yaml.safe_load(COMPOSE.read_text())["secrets"]
    assert top[SOURCE] == {"file": "${EXTRA_CA_FILE:-/dev/null}"}


@pytest.mark.unit
def test_readme_run_it_locally_documents_extra_ca_file_make_up() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    section = readme.split("## Run it locally", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"EXTRA_CA_FILE=\S+ make up", section)


# ---------------------------------------------------------------- IT-04-14 (real docker)
@pytest.mark.integration
@needs_docker
def test_it_04_14_without_extra_ca_file_no_service_gets_the_secret(tmp_path: Path) -> None:
    config = render(env_file(tmp_path, None))
    ids = rendered_secret_ids(config)
    assert sorted(ids) == ["api", "mailer", "migrate", "purge", "web", "worker"]
    assert all(SECRET_ID not in v for v in ids.values()), ids
    assert config["secrets"][SOURCE]["file"] == "/dev/null"


@pytest.mark.integration
@needs_docker
def test_it_04_14_with_extra_ca_file_every_service_gets_it(tmp_path: Path) -> None:
    ca = make_ca(tmp_path)
    config = render(env_file(tmp_path, ca))
    ids = rendered_secret_ids(config)
    assert ids
    assert all(SECRET_ID in v for v in ids.values()), ids
    assert config["secrets"][SOURCE]["file"] == str(ca)


@pytest.mark.integration
@needs_docker
def test_it_04_14_a_build_without_extra_ca_file_mounts_nothing(tmp_path: Path) -> None:
    ca = make_ca(tmp_path)  # on disk, not configured
    probe = probe_build(tmp_path, env_file(tmp_path, None))
    assert probe.seen == "none"
    assert not holds_certificate(probe, ca)


@pytest.mark.integration
@needs_docker
def test_it_04_14_a_build_with_a_throwaway_ca_reads_it_and_no_layer_has_it(tmp_path: Path) -> None:
    ca = make_ca(tmp_path)
    probe = probe_build(tmp_path, env_file(tmp_path, ca))
    assert probe.seen == sha256(ca)
    assert any(probe.seen.encode() in layer for layer in probe.layers), "layer search reads nothing"
    assert not holds_certificate(probe, ca)
