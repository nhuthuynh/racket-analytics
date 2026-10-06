"""Built images honour ``DOCKERHUB_REGISTRY`` too (Sprint 1 integration smoke, smoke.md §6).

``infra/env.example`` says to set ``DOCKERHUB_REGISTRY=mirror.gcr.io`` when Docker Hub
rate-limits. The pulled services (postgres, seaweedfs, mailpit, jaeger, caddy) honour it, but the
five built services (migrate, api, worker, mailer, web) took their base images and the
``# syntax=`` frontend from Docker Hub regardless, so a fresh ``up --build`` failed with
``429 Too Many Requests`` on ``node:22-slim``. Each build now passes its base image and the
Dockerfile frontend through the same registry variable; with the default ``docker.io`` the
resolved references are the Dockerfile defaults, so CI is unchanged.
"""

from __future__ import annotations

import re

import pytest
import yaml
from conftest import REPO_ROOT
from test_compose import COMPOSE

REG = "${DOCKERHUB_REGISTRY:-docker.io}"


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def built() -> dict[str, dict]:
    return {name: svc["build"] for name, svc in services().items() if "build" in svc}


def dockerfile_defaults(dockerfile: str) -> tuple[str, dict[str, str]]:
    """The ``# syntax=`` frontend and every ``ARG NAME=default`` of a Dockerfile."""
    text = (REPO_ROOT / dockerfile).read_text()
    syntax = re.search(r"^# syntax=(\S+)$", text, re.M)
    args = dict(re.findall(r"^ARG (\w+)=(\S+)$", text, re.M))
    return (syntax.group(1) if syntax else ""), args


BASE_ARG = {
    "infra/docker/backend.Dockerfile": "PYTHON_IMAGE",
    "infra/docker/web.Dockerfile": "NODE_IMAGE",
}


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_no_built_service_pulls_its_base_image_from_docker_hub_unconditionally() -> None:
    offenders = []
    for name, build in built().items():
        args = build.get("args") or {}
        base = args.get(BASE_ARG[build["dockerfile"]], "")
        if not base.startswith(f"{REG}/library/"):
            offenders.append(name)
    assert offenders == [], f"base image ignores DOCKERHUB_REGISTRY: {offenders}"


@pytest.mark.unit
def test_no_built_service_pulls_the_dockerfile_frontend_from_docker_hub_unconditionally() -> None:
    offenders = [
        name
        for name, build in built().items()
        if not (build.get("args") or {}).get("BUILDKIT_SYNTAX", "").startswith(f"{REG}/docker/dockerfile:")
    ]
    assert offenders == [], f"syntax frontend ignores DOCKERHUB_REGISTRY: {offenders}"


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_the_five_app_services_are_the_built_ones() -> None:
    assert sorted(built()) == ["api", "mailer", "migrate", "web", "worker"]


@pytest.mark.unit
def test_with_the_default_registry_the_references_equal_the_dockerfile_defaults() -> None:
    """``docker.io/library/x`` is ``x``: CI (no override) builds from exactly the same images."""
    for name, build in built().items():
        syntax, defaults = dockerfile_defaults(build["dockerfile"])
        arg = BASE_ARG[build["dockerfile"]]
        args = build["args"]
        assert args[arg] == f"{REG}/library/{defaults[arg]}", name
        assert args["BUILDKIT_SYNTAX"] == f"{REG}/{syntax}", name
