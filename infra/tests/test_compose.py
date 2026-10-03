"""ST-001: infra/compose.yaml brings up the full stack with production's backing services,
configured only through environment variables [AQS/OPS-01, AQS/OPS-05]."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

COMPOSE = REPO_ROOT / "infra" / "compose.yaml"
ENV_EXAMPLE = REPO_ROOT / "infra" / "env.example"
SERVICES = {"postgres", "objectstore", "mailpit", "api", "worker", "web"}

needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI missing")


def compose_config(env_file: Path) -> subprocess.CompletedProcess[str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.isupper() or k in {"PATH", "HOME", "DOCKER_HOST"}
    }
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "--env-file", str(env_file), "config"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def raw() -> dict:
    return yaml.safe_load(COMPOSE.read_text())


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
@needs_docker
@pytest.mark.parametrize("missing", ["POSTGRES_PASSWORD", "S3_SECRET_ACCESS_KEY", "APP_ENV"])
def test_missing_required_variable_stops_compose_and_names_it(tmp_path: Path, missing: str) -> None:
    lines = [ln for ln in ENV_EXAMPLE.read_text().splitlines() if not ln.startswith(f"{missing}=")]
    env_file = tmp_path / "partial.env"
    env_file.write_text("\n".join(lines) + "\n")
    res = compose_config(env_file)
    assert res.returncode != 0
    assert missing in res.stderr


@pytest.mark.unit
def test_no_sqlite_anywhere_in_infra() -> None:
    for path in (REPO_ROOT / "infra").rglob("*"):
        skip = {"tests", ".venv", ".pytest_cache", ".ruff_cache"}
        if (
            path.is_file()
            and not skip & set(path.parts)
            and path.suffix in {".yaml", ".yml", ".example", ".Dockerfile", ""}
        ):
            code = [
                ln
                for ln in path.read_text(errors="ignore").lower().splitlines()
                if not ln.lstrip().startswith("#")
            ]
            assert not any("sqlite" in ln for ln in code), path


@pytest.mark.unit
def test_compose_file_contains_no_literal_secrets() -> None:
    text = COMPOSE.read_text()
    for m in re.finditer(r"(?im)^\s*[-\w]*(PASSWORD|SECRET|TOKEN|KEY)[\w]*\s*[:=]\s*(.+)$", text):
        assert "${" in m.group(2), m.group(0)


@pytest.mark.unit
def test_published_ports_bind_to_localhost_only() -> None:
    for name, svc in raw()["services"].items():
        for port in svc.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), (name, port)


@pytest.mark.unit
def test_worker_is_only_on_the_internal_sandbox_network() -> None:
    doc = raw()
    nets = doc["services"]["worker"]["networks"]
    names = list(nets) if isinstance(nets, dict) else nets
    assert names, "worker must declare networks"
    for n in names:
        assert doc["networks"][n].get("internal") is True, n
    assert not doc["services"]["worker"].get("ports")


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
@needs_docker
def test_full_stack_config_is_valid_with_the_example_env() -> None:
    res = compose_config(ENV_EXAMPLE)
    assert res.returncode == 0, res.stderr
    services = set(yaml.safe_load(res.stdout)["services"])
    assert services >= SERVICES


@pytest.mark.unit
def test_every_service_has_a_healthcheck_or_completes() -> None:
    for name, svc in raw()["services"].items():
        assert "healthcheck" in svc or svc.get("restart") == "no", name


@pytest.mark.unit
def test_app_services_wait_for_healthy_backing_services() -> None:
    svcs = raw()["services"]
    for app in ("api", "worker"):
        deps = svcs[app]["depends_on"]
        assert deps["postgres"]["condition"] == "service_healthy"
        assert deps["objectstore-init"]["condition"] == "service_completed_successfully"


@pytest.mark.unit
def test_env_example_has_no_real_looking_secrets() -> None:
    for line in ENV_EXAMPLE.read_text().splitlines():
        if re.match(r"^[A-Z_]*(PASSWORD|SECRET)[A-Z_]*=", line):
            assert "dev-only" in line, line
