"""Sprint 2 platform rows on the Compose stack (sprint-02 §3: C-11, C-18, C-13, SRE-MEDIA).

C-11 (SEC-R6-S1-02): the API's own port is published for the server-side latency methods
(G02-04, NFR-010), but the per-IP sign-in limit (T-ML-8) holds only behind web-tls, which
replaces any client ``X-Forwarded-For``. A caller on the API port can choose its own
right-most entry. So the port stays on loopback, and the limit's scope is written where an
operator sets the port.
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT
from test_compose import COMPOSE, ENV_EXAMPLE, compose_config, needs_docker

OPS_EVIDENCE = REPO_ROOT / "docs" / "ops" / "evidence-runs.md"


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def env_example() -> dict[str, str]:
    lines = ENV_EXAMPLE.read_text().splitlines()
    return dict(ln.split("=", 1) for ln in lines if ln and ln[0] != "#")


def comment_block_before(text: str, marker: str) -> str:
    """The run of ``#`` comment lines right above the first line containing ``marker``."""
    lines = text.splitlines()
    idx = next(i for i, ln in enumerate(lines) if marker in ln)
    block: list[str] = []
    for ln in reversed(lines[:idx]):
        if not ln.strip().startswith("#"):
            break
        block.append(ln)
    return "\n".join(reversed(block))


# ---------------------------------------------------------------- C-11, negative first
@pytest.mark.unit
def test_api_port_is_published_on_loopback_only_and_nowhere_else() -> None:
    assert services()["api"]["ports"] == ["127.0.0.1:${API_HOST_PORT:-8000}:8000"]


@pytest.mark.unit
def test_compose_says_the_per_ip_limit_holds_only_behind_web_tls() -> None:
    block = comment_block_before(COMPOSE.read_text(), "127.0.0.1:${API_HOST_PORT")
    assert "T-ML-8" in block, block
    assert "web-tls" in block, block
    assert "X-Forwarded-For" in block, block


@pytest.mark.unit
def test_env_example_says_the_api_port_is_for_server_side_measurement_only() -> None:
    block = comment_block_before(ENV_EXAMPLE.read_text(), "API_HOST_PORT=")
    assert "T-ML-8" in block, block
    assert "web-tls" in block, block


@pytest.mark.unit
@needs_docker
def test_rendered_api_port_binds_loopback() -> None:
    res = compose_config(ENV_EXAMPLE)
    assert res.returncode == 0, res.stderr
    ports = yaml.safe_load(res.stdout)["services"]["api"]["ports"]
    assert [p["host_ip"] for p in ports] == ["127.0.0.1"]


# ---------------------------------------------------------------- C-18 (SEC-R5-S1-03)
# Without ALLOWED_ORIGINS the API's origin check is off (empty set = allow all), so the dev
# and CI E2E stacks never exercised it. env.example is also the CI E2E env (ci.yml COMPOSE).
@pytest.mark.unit
def test_env_example_allows_exactly_the_web_origin() -> None:
    assert env_example()["ALLOWED_ORIGINS"] == "${PUBLIC_WEB_ORIGIN}"


@pytest.mark.unit
def test_compose_requires_allowed_origins_for_the_api() -> None:
    env = services()["api"]["environment"]
    assert env.get("ALLOWED_ORIGINS", "").startswith("${ALLOWED_ORIGINS:?"), env


@pytest.mark.unit
@needs_docker
def test_rendered_api_allows_the_https_web_origin_only() -> None:
    res = compose_config(ENV_EXAMPLE)
    assert res.returncode == 0, res.stderr
    env = yaml.safe_load(res.stdout)["services"]["api"]["environment"]
    assert env["ALLOWED_ORIGINS"] == "https://localhost:3000"
    assert env["ALLOWED_ORIGINS"] == env["PUBLIC_WEB_ORIGIN"]


@pytest.mark.unit
@needs_docker
def test_a_remapped_web_origin_carries_the_allowed_origin_with_it(tmp_path) -> None:
    # goal-scorecard §4.0 rewrites https://localhost:3000 to the remapped port with one sed.
    remapped = tmp_path / "goal.env"
    remapped.write_text(
        ENV_EXAMPLE.read_text().replace("https://localhost:3000", "https://localhost:33000")
    )
    res = compose_config(remapped)
    assert res.returncode == 0, res.stderr
    env = yaml.safe_load(res.stdout)["services"]["api"]["environment"]
    assert env["ALLOWED_ORIGINS"] == "https://localhost:33000"


# ---------------------------------------------------------------- SRE-MEDIA (FR-027, NFR-055)
# The API presigns media GETs for S3_PUBLIC_ENDPOINT_URL (decision-log "ST-037 media links").
# web-tls serves /<bucket>/* from the store on the web origin, so the page CSP
# `media-src 'self'` allows the video and no CORS rule is needed. A presigned URL signs host
# and path, so the proxy must forward both unchanged.
CADDYFILE = REPO_ROOT / "infra" / "tls" / "Caddyfile"


def caddy_lines() -> list[str]:
    lines = (ln.split("#", 1)[0].strip() for ln in CADDYFILE.read_text().splitlines())
    return [ln for ln in lines if ln]


def media_block() -> list[str]:
    """Directives from the media matcher up to the catch-all web handler."""
    lines = caddy_lines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("@media"))
    end = next(i for i, ln in enumerate(lines) if "reverse_proxy web:3000" in ln)
    assert start < end, "the media route must come before the web catch-all"
    return lines[start:end]


@pytest.mark.unit
def test_media_route_matches_only_the_bucket_path() -> None:
    assert "@media path /{$S3_BUCKET_MEDIA}/*" in caddy_lines()


@pytest.mark.unit
def test_media_route_forwards_only_presigned_get_and_head() -> None:
    block = media_block()
    assert "method GET HEAD" in block, block
    assert "query X-Amz-Signature=*" in block, block
    # anything else on the bucket path is refused at the edge, never sent to the store or web
    assert "respond 403" in block, block


@pytest.mark.unit
def test_media_route_keeps_path_and_host() -> None:
    joined = "\n".join(media_block())
    assert "reverse_proxy objectstore:8333" in joined
    for rewrite in ("strip_prefix", "handle_path", "rewrite", "header_up Host"):
        assert rewrite not in joined, rewrite


@pytest.mark.unit
@pytest.mark.parametrize("header", ["Cookie", "Authorization"])
def test_media_route_never_sends_credentials_to_the_store(header: str) -> None:
    assert f"header_up -{header}" in media_block()


@pytest.mark.unit
@pytest.mark.parametrize(
    "header",
    [
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials",
        # measured live 2026-10-06: SeaweedFS adds these to every GET, even same-origin
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers",
        "Access-Control-Expose-Headers",
    ],
)
def test_media_route_adds_no_cross_origin_access(header: str) -> None:
    # same origin only: any CORS grant from the store is dropped at the edge
    assert f"header_down -{header}" in media_block()


@pytest.mark.unit
def test_media_route_hides_the_store_version() -> None:
    # live 2026-10-06: `Server: SeaweedFS 30GB 3.97` reached the browser [AQS/SEC-06]
    assert "header_down -Server" in media_block()


@pytest.mark.unit
def test_media_links_are_signed_for_the_web_origin() -> None:
    assert env_example()["S3_PUBLIC_ENDPOINT_URL"] == "${PUBLIC_WEB_ORIGIN}"


@pytest.mark.unit
def test_web_tls_knows_the_bucket_and_the_api_gets_the_ttl_from_config() -> None:
    svc = services()
    assert svc["web-tls"]["environment"]["S3_BUCKET_MEDIA"].startswith("${S3_BUCKET_MEDIA:?")
    ttl = svc["api"]["environment"]["MEDIA_URL_TTL_SECONDS"]
    assert ttl.startswith("${MEDIA_URL_TTL_SECONDS:-")
    assert int(ttl.split(":-", 1)[1].rstrip("}")) <= 900  # NFR-055


@pytest.mark.unit
@needs_docker
def test_rendered_media_endpoint_follows_a_remapped_web_origin(tmp_path) -> None:
    remapped = tmp_path / "goal.env"
    remapped.write_text(
        ENV_EXAMPLE.read_text().replace("https://localhost:3000", "https://localhost:33000")
    )
    res = compose_config(remapped)
    assert res.returncode == 0, res.stderr
    rendered = yaml.safe_load(res.stdout)["services"]
    assert rendered["api"]["environment"]["S3_PUBLIC_ENDPOINT_URL"] == "https://localhost:33000"
    assert rendered["web-tls"]["environment"]["S3_BUCKET_MEDIA"] == "racket-media"


# ---------------------------------------------------------------- C-13 (SRE-G2-01)
# FastAPI's automatic telemetry (fastapi/telemetry/_runtime.py) derives
# {OTEL_EXPORTER_OTLP_ENDPOINT}/v1/metrics and /v1/logs and exports there. Jaeger takes traces
# only, so every minute the API logged "Failed to export metrics batch code: 404" (measured
# live 2026-10-06 on racket-sre02). The dev stack has no metrics backend: those two signals are
# off. The SLI metrics still export when OTEL_EXPORTER_OTLP_METRICS_ENDPOINT names a collector
# (racket.platform.slis.configure_metrics reads only that variable).
@pytest.mark.unit
@pytest.mark.parametrize("signal", ["OTEL_METRICS_EXPORTER", "OTEL_LOGS_EXPORTER"])
def test_signals_jaeger_cannot_take_are_off_for_every_app_service(signal: str) -> None:
    for name in ("api", "worker", "mailer"):
        env = services()[name]["environment"]
        assert env.get(signal) == "none", (name, signal)


@pytest.mark.unit
def test_traces_still_go_to_jaeger() -> None:
    env = services()["api"]["environment"]
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://tracing:4318"
    assert env.get("OTEL_TRACES_EXPORTER", "otlp") != "none"
