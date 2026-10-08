"""SEC-RV3-02 (T-ML-7; NFR-056): the production entrypoint, ``uvicorn racket.platform.app:app``
as the api image runs it (infra/docker/backend.Dockerfile), refuses to start in staging and prod
on the dev-only AUTH_EMAIL_KEY of infra/env.example, and never prints the key. A real key on the
same environment serves /healthz. Real process, real environment, real Postgres address.
Negative cases first.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time

import httpx
import pytest

pytestmark = pytest.mark.integration

ENV_EXAMPLE_KEY = "dev-only-email-key-not-a-secret-0000"
REAL_KEY = "".join(chr(ord("a") + (i * 11) % 26) for i in range(40))  # made up, not dev-only


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _deployed_env(app_env: str, key: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("APP_", "AUTH_", "DEV_"))}
    env.update(
        APP_ENV=app_env,
        AUTH_EMAIL_KEY=key,
        DEV_IDENTITY_ENABLED="false",
        DATABASE_URL=os.environ["DATABASE_URL"],
        S3_BUCKET_MEDIA=os.environ.get("S3_BUCKET_MEDIA", "racket-media"),
        ALLOWED_ORIGINS="https://app.racket.test",
        PUBLIC_WEB_ORIGIN="https://app.racket.test",
    )
    return env


def _uvicorn(env: dict[str, str], port: int) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "racket.platform.app:app", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


@pytest.mark.parametrize("app_env", ["staging", "prod"])
def test_the_api_process_refuses_the_dev_email_key_when_deployed(app_env: str) -> None:
    proc = _uvicorn(_deployed_env(app_env, ENV_EXAMPLE_KEY), _free_port())
    try:
        output, _ = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        output, _ = proc.communicate()
        pytest.fail(f"the API kept running in {app_env} on the dev-only key:\n{output[-2000:]}")
    assert proc.returncode != 0, output[-2000:]
    assert "AUTH_EMAIL_KEY is a dev placeholder" in output, output[-2000:]
    assert ENV_EXAMPLE_KEY not in output


def test_positive_control_the_api_process_serves_with_a_real_key_in_prod() -> None:
    port = _free_port()
    proc = _uvicorn(_deployed_env("prod", REAL_KEY), port)
    try:
        deadline = time.monotonic() + 60
        while True:
            assert proc.poll() is None, proc.communicate()[0][-2000:]
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=2)
                break
            except httpx.TransportError:
                assert time.monotonic() < deadline, "the API did not answer /healthz in 60 s"
                time.sleep(0.2)
        assert response.status_code == 200
    finally:
        proc.terminate()
        proc.wait(timeout=30)
