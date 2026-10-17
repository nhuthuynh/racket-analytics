"""Binds tests/features/compose_extra_ca.feature (C4-CA, VR3-S3-01). Negative case first.

"The stack images are built" = the real ``docker compose config`` of infra/compose.yaml (what
each built service would hand BuildKit) plus one real probe build through that wiring; see
``extra_ca_fixtures``. The full stack build behind the sandbox proxy is in the PR evidence.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from extra_ca_fixtures import (
    env_file,
    holds_certificate,
    make_ca,
    probe_build,
    render,
    rendered_secret_ids,
    sha256,
)
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [
    pytest.mark.scenario,
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI missing"),
]
scenarios("compose_extra_ca.feature")


@given("no extra CA file is configured", target_fixture="ctx")
def no_extra_ca(tmp_path: Path) -> dict:
    # A CA exists on disk but is not configured: it must not reach any image.
    return {"ca": make_ca(tmp_path), "env": env_file(tmp_path, None), "tmp": tmp_path}


@given("EXTRA_CA_FILE names a CA certificate", target_fixture="ctx")
def extra_ca_configured(tmp_path: Path) -> dict:
    ca = make_ca(tmp_path)
    return {"ca": ca, "env": env_file(tmp_path, ca), "tmp": tmp_path}


@when("the stack images are built")
def build(ctx: dict) -> None:
    ctx["ids"] = rendered_secret_ids(render(ctx["env"]))
    ctx["probe"] = probe_build(ctx["tmp"], ctx["env"])


@then(parsers.parse('no build service receives the secret "{secret}"'))
def no_service_receives(ctx: dict, secret: str) -> None:
    assert ctx["ids"], "no build services rendered"
    assert [n for n, ids in ctx["ids"].items() if secret in ids] == []


@then(parsers.parse('every build service receives the secret "{secret}"'))
def every_service_receives(ctx: dict, secret: str) -> None:
    assert ctx["ids"], "no build services rendered"
    assert [n for n, ids in ctx["ids"].items() if secret not in ids] == []


@then(parsers.parse('the probe build saw no secret "{secret}"'))
def probe_saw_none(ctx: dict, secret: str) -> None:
    assert ctx["probe"].seen == "none", f"{secret} was mounted: sha256 {ctx['probe'].seen}"


@then(parsers.parse('the probe build read that certificate as the secret "{secret}"'))
def probe_saw_ca(ctx: dict, secret: str) -> None:
    assert ctx["probe"].seen == sha256(ctx["ca"]), f"{secret}: {ctx['probe'].seen}"


@then("no image layer holds the certificate")
def no_layer_holds_ca(ctx: dict) -> None:
    probe = ctx["probe"]
    # Control: the search reads layer contents (the recorded hash is in a layer).
    assert any(probe.seen.encode() in layer for layer in probe.layers)
    assert not holds_certificate(probe, ctx["ca"])
