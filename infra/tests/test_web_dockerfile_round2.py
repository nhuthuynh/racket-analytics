"""Review round 2 (QA-R2-03): the web image must build behind a TLS-intercepting proxy, like
the backend image. Every RUN step that reaches the network (corepack fetching pnpm,
``pnpm install``, ``pnpm build``) mounts the optional ``extra_ca`` build secret and hands it
to Node through ``NODE_EXTRA_CA_CERTS``. Without the secret the build is unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB_DOCKERFILE = Path(__file__).resolve().parents[1] / "docker" / "web.Dockerfile"
NETWORK_COMMANDS = ("pnpm install", "pnpm build")
SECRET_MOUNT = "--mount=type=secret,id=extra_ca,required=false"


def run_steps(text: str) -> list[str]:
    """RUN instructions with line continuations joined."""
    joined = re.sub(r"\\\n", " ", text)
    return [ln.strip() for ln in joined.splitlines() if ln.strip().startswith("RUN ")]


@pytest.mark.unit
def test_a_network_step_without_the_ca_secret_is_detected() -> None:
    bad = "FROM node\nRUN pnpm install --frozen-lockfile\n"

    missing = [s for s in run_steps(bad) if any(c in s for c in NETWORK_COMMANDS)]

    assert missing
    assert SECRET_MOUNT not in missing[0]


@pytest.mark.unit
@pytest.mark.parametrize("command", NETWORK_COMMANDS)
def test_every_network_step_mounts_the_optional_ca_secret(command: str) -> None:
    steps = [s for s in run_steps(WEB_DOCKERFILE.read_text()) if command in s]

    assert steps, f"no RUN step runs {command!r}"
    for step in steps:
        assert SECRET_MOUNT in step, step
        assert "NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca" in step, step
        assert "if [ -f /run/secrets/extra_ca ]" in step, step  # optional: absent → unchanged


@pytest.mark.unit
def test_the_dockerfile_enables_buildkit_secret_syntax() -> None:
    assert WEB_DOCKERFILE.read_text().startswith("# syntax=docker/dockerfile:1.7")


def runtime_stage(text: str) -> str:
    return text.split(" AS runtime", 1)[1]


@pytest.mark.unit
def test_runtime_start_needs_no_network() -> None:
    """Found while building the image for QA-R2-03: ``CMD ["pnpm", "start"]`` made corepack
    download pnpm from registry.npmjs.org at *container start* (a fresh stage has no pnpm),
    which fails with no egress or behind a TLS proxy. The runtime runs Next.js with node."""
    runtime = runtime_stage(WEB_DOCKERFILE.read_text())
    cmd = [ln for ln in runtime.splitlines() if ln.startswith("CMD ")]

    assert cmd
    assert "pnpm" not in cmd[-1], cmd
    assert "corepack" not in cmd[-1], cmd
    assert "corepack enable" not in runtime
    assert '"node", "node_modules/next/dist/bin/next", "start"' in cmd[-1]


@pytest.mark.unit
def test_runtime_image_ships_no_next_build_cache() -> None:
    """C-15 (disk): the runtime copies the whole build stage, so ``.next/cache`` went into every
    web image. Dev dependencies must stay: ``next start`` needs TypeScript for next.config.ts."""
    text = WEB_DOCKERFILE.read_text()
    build = text.split(" AS build", 1)[1].split(" AS runtime", 1)[0]
    steps = run_steps(build)
    build_step = next(s for s in steps if "pnpm build" in s)
    assert "rm -rf .next/cache" in build_step, build_step
    assert build_step.index("pnpm build") < build_step.index("rm -rf .next/cache")
    assert "prune --prod" not in build_step


@pytest.mark.unit
@pytest.mark.parametrize(
    "pattern",
    ["**/test-results", "**/playwright-report", "**/blob-report", "**/coverage", "reports"],
)
def test_build_context_leaves_out_local_test_output(pattern: str) -> None:
    """C-15 (disk): ``COPY web/ ./`` carried ``web/test-results`` (809 MB of local Playwright
    output, measured 2026-10-06) into every web image and every evidence round."""
    ignore = (WEB_DOCKERFILE.parents[2] / ".dockerignore").read_text().splitlines()
    assert pattern in ignore
