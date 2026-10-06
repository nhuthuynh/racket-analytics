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
    remapped.write_text(ENV_EXAMPLE.read_text().replace("https://localhost:3000", "https://localhost:33000"))
    res = compose_config(remapped)
    assert res.returncode == 0, res.stderr
    env = yaml.safe_load(res.stdout)["services"]["api"]["environment"]
    assert env["ALLOWED_ORIGINS"] == "https://localhost:33000"
