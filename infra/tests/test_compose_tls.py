"""The dev/E2E stack is served over https (ADR 0029; blockers.md 2026-10-05 "E2E WebKit cannot
sign in over http://localhost").

Outside ``APP_ENV=test`` the API sets ``__Host-racket_session`` with ``Secure``. WebKit drops a
``Secure`` cookie set over plain ``http://localhost`` (CI run 37277549983), so the browser entry
point is a TLS-terminating proxy (Caddy, ``tls internal``) in front of the web. Its CA and leaf
key are generated inside the container at start; no private key is ever committed.
"""

from __future__ import annotations

import re
import subprocess

import pytest
import yaml
from conftest import REPO_ROOT
from test_compose import COMPOSE, ENV_EXAMPLE, compose_config, needs_docker

CADDYFILE = REPO_ROOT / "infra" / "tls" / "Caddyfile"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def env_example() -> dict[str, str]:
    lines = ENV_EXAMPLE.read_text().splitlines()
    return dict(ln.split("=", 1) for ln in lines if ln and ln[0] != "#")


def caddy_directives() -> list[str]:
    """Caddyfile lines without comments or blank lines."""
    lines = (ln.split("#", 1)[0].strip() for ln in CADDYFILE.read_text().splitlines())
    return [ln for ln in lines if ln]


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_the_web_is_not_reachable_from_the_host_over_plain_http() -> None:
    # The only browser entry point is the TLS proxy: a second, plain-http door would let a
    # browser sign in without Secure cookies and bypass the proxy's X-Forwarded-For reset.
    assert "ports" not in services()["web"]


@pytest.mark.unit
def test_no_private_key_or_certificate_is_committed() -> None:
    tracked = (
        subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True)
        .stdout.decode()
        .split("\0")
    )
    offenders = []
    for rel in filter(None, tracked):
        path = REPO_ROOT / rel
        if path.suffix in {".key", ".pem", ".p12", ".pfx", ".crt"}:
            offenders.append(rel)
            continue
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", text) and "tests" not in rel:
            offenders.append(rel)
    assert offenders == []


@pytest.mark.unit
def test_the_proxy_never_trusts_a_client_supplied_forwarded_for() -> None:
    # Caddy replaces X-Forwarded-For unless trusted_proxies is set; the API's per-IP sign-in
    # limits rely on the proxy's value (T-ML-8).
    assert not any("trusted_proxies" in ln for ln in caddy_directives())


@pytest.mark.unit
def test_the_proxy_uses_its_own_internal_ca_and_never_requests_public_certificates() -> None:
    directives = caddy_directives()
    assert "tls internal" in directives
    assert not any(ln.startswith(("email", "acme_ca", "acme_dns")) for ln in directives)
    # The CA lives only in the container; it is never installed into a host trust store.
    assert "skip_install_trust" in directives


@pytest.mark.unit
def test_the_ci_e2e_job_never_targets_plain_http() -> None:
    steps = yaml.safe_load(CI.read_text())["jobs"]["e2e"]["steps"]
    for step in steps:
        base = step.get("env", {}).get("BASE_URL")
        if base is not None:
            assert base.startswith("https://"), step.get("name")


def e2e_steps() -> list[dict]:
    return yaml.safe_load(CI.read_text())["jobs"]["e2e"]["steps"]


@pytest.mark.unit
def test_ci_never_copies_the_dev_ca_private_key() -> None:
    for step in e2e_steps():
        run = step.get("run", "")
        assert "root.key" not in run, step.get("name")
        assert "intermediate.key" not in run, step.get("name")


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_the_tls_proxy_is_the_browser_entry_point() -> None:
    proxy = services()["web-tls"]
    assert proxy["image"].startswith("${DOCKERHUB_REGISTRY:-docker.io}/library/caddy:")
    assert proxy["ports"] == ["127.0.0.1:${WEB_HOST_PORT:-3000}:443"]
    assert proxy["networks"] == ["edge"]
    assert proxy["depends_on"]["web"]["condition"] == "service_healthy"
    assert "healthcheck" in proxy
    mounts = proxy["volumes"]
    assert "./tls/Caddyfile:/etc/caddy/Caddyfile:ro" in mounts
    # The generated CA persists in a named volume, so a restart keeps the same trust anchor.
    assert any(m.startswith("caddy-data:/data") for m in mounts)
    assert "caddy-data" in yaml.safe_load(COMPOSE.read_text())["volumes"]


@pytest.mark.unit
def test_the_proxy_forwards_to_the_web_on_the_internal_network() -> None:
    directives = caddy_directives()
    assert "reverse_proxy web:3000" in directives
    assert "admin off" in directives


@pytest.mark.unit
def test_the_api_takes_the_client_address_web_tls_wrote() -> None:
    # Browser -> web-tls (replaces X-Forwarded-For with the peer) -> web /api rewrite (forwards
    # it unchanged) -> api. Measured on the stack 2026-10-05 with a header echo in place of the
    # API: a forged "X-Forwarded-For: 203.0.113.9" arrived as the host gateway address only.
    assert str(services()["api"]["environment"]["TRUSTED_PROXY_HOPS"]) == "1"


@pytest.mark.unit
def test_env_example_points_sign_in_links_at_the_https_origin() -> None:
    assert env_example()["PUBLIC_WEB_ORIGIN"] == "https://localhost:3000"


@pytest.mark.unit
def test_the_ci_e2e_job_targets_the_https_origin() -> None:
    steps = yaml.safe_load(CI.read_text())["jobs"]["e2e"]["steps"]
    bases = [s["env"]["BASE_URL"] for s in steps if "BASE_URL" in s.get("env", {})]
    assert bases == ["https://localhost:3000"]


@pytest.mark.unit
@needs_docker
def test_compose_config_renders_the_tls_proxy_with_the_example_env() -> None:
    res = compose_config(ENV_EXAMPLE)
    assert res.returncode == 0, res.stderr
    rendered = yaml.safe_load(res.stdout)["services"]
    assert rendered["web-tls"]["ports"][0]["published"] == "3000"
    assert rendered["web-tls"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert rendered["api"]["environment"]["PUBLIC_WEB_ORIGIN"] == "https://localhost:3000"


@pytest.mark.unit
def test_ci_trusts_the_dev_root_certificate_before_the_browsers_run() -> None:
    # WebKit and the service worker need a certificate the runner actually trusts; only the
    # public root certificate leaves the container (ADR 0029).
    steps = e2e_steps()
    names = [s.get("name", "") for s in steps]
    trust = next(
        i
        for i, s in enumerate(steps)
        if "/data/caddy/pki/authorities/local/root.crt" in s.get("run", "")
    )
    start = names.index("Start the full stack")
    playwright = next(i for i, n in enumerate(names) if n.startswith("Playwright journeys"))
    assert start < trust < playwright
    run = steps[trust]["run"]
    assert "update-ca-certificates" in run
    # Proof the chain validates without -k: a plain curl over https must succeed.
    assert re.search(r"curl --fail[^\n]*https://localhost:3000/", run)
    assert " -k" not in run
    assert "--insecure" not in run
