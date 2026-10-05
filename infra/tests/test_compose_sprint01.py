"""Sprint 1 Compose wiring for ST-013 (ADR 0027; api-sprint-01 §8, §9 row 5; blockers.md
2026-10-05, senior-backend-engineer).

* The sign-in email needs SMTP, so ``send_sign_in_link`` runs in a ``mailer`` worker on the
  ``edge`` network. The media sandbox ``worker`` has no route to Mailpit and must run ``probe``
  only, or it claims sign-in jobs and fails them ``mail_failed``.
* The API builds the link from ``PUBLIC_WEB_ORIGIN`` and sits behind the web's ``/api`` rewrite
  (one proxy hop), so ``TRUSTED_PROXY_HOPS=1`` keeps per-IP rate limits on the client address.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from test_compose import COMPOSE, ENV_EXAMPLE, compose_config, needs_docker


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def env_example() -> dict[str, str]:
    lines = ENV_EXAMPLE.read_text().splitlines()
    return dict(ln.split("=", 1) for ln in lines if ln and ln[0] != "#")


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_the_sandboxed_worker_never_claims_sign_in_email_jobs() -> None:
    env = services()["worker"]["environment"]
    assert env.get("WORKER_STAGES") == "probe"


@pytest.mark.unit
def test_the_mailer_cannot_run_media_stages() -> None:
    env = services()["mailer"]["environment"]
    assert env.get("WORKER_STAGES") == "send_sign_in_link"


@pytest.mark.unit
@needs_docker
def test_compose_refuses_to_start_without_the_public_web_origin(tmp_path: Path) -> None:
    lines = [
        ln for ln in ENV_EXAMPLE.read_text().splitlines() if not ln.startswith("PUBLIC_WEB_ORIGIN=")
    ]
    env_file = tmp_path / "partial.env"
    env_file.write_text("\n".join(lines) + "\n")

    res = compose_config(env_file)

    assert res.returncode != 0
    assert "PUBLIC_WEB_ORIGIN" in res.stderr


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_the_mailer_reaches_mailpit_and_starts_after_the_schema() -> None:
    mailer = services()["mailer"]
    assert mailer["command"] == ["python", "-m", "racket.worker"]
    assert mailer["build"]["target"] == "api"
    assert mailer["networks"] == ["edge"]
    assert mailer["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert mailer["depends_on"]["mailpit"]["condition"] == "service_healthy"
    assert mailer["environment"]["MAIL_SMTP_URL"] == "smtp://mailpit:1025"
    assert mailer.get("restart") in {"unless-stopped", "on-failure", "always"}


@pytest.mark.unit
def test_the_api_and_mailer_share_the_sign_in_settings() -> None:
    svcs = services()
    for name in ("api", "mailer"):
        env = svcs[name]["environment"]
        for key in ("PUBLIC_WEB_ORIGIN", "MAIL_FROM", "AUTH_EMAIL_KEY"):
            assert key in env, (name, key)
    assert str(svcs["api"]["environment"]["TRUSTED_PROXY_HOPS"]) == "1"


@pytest.mark.unit
def test_env_example_documents_the_sprint_1_settings() -> None:
    env = env_example()
    assert env["PUBLIC_WEB_ORIGIN"] == "https://localhost:3000"  # ADR 0029
    assert env["MAIL_FROM"]
    # Dev placeholder only; staging/prod need >= 32 characters from the secret store.
    assert len(env["AUTH_EMAIL_KEY"]) >= 32


@pytest.mark.unit
@needs_docker
def test_compose_config_renders_with_the_example_env() -> None:
    res = compose_config(ENV_EXAMPLE)
    assert res.returncode == 0, res.stderr
    rendered = yaml.safe_load(res.stdout)["services"]
    assert rendered["mailer"]["environment"]["PUBLIC_WEB_ORIGIN"] == "https://localhost:3000"


# ---------------------------------------------------------------- E2E rate limits (smoke 2026-10-05)
# Every Playwright test signs in from the same host IP, so the per-IP sign-in limits (20 link
# requests per 10 min) refuse the suite after about 20 sign-ins: 16 Sprint 1 journeys failed with
# "You have asked for too many links" in the first integrated smoke (docs/sprints/01/smoke.md).
# The per-email limit (5) stays at its default so "Too many link requests" is still exercised;
# the per-IP limit is covered at API level (IT-01-02).
@pytest.mark.unit
def test_per_ip_sign_in_limits_keep_the_contract_defaults_unless_overridden() -> None:
    env = services()["api"]["environment"]
    assert env["AUTH_LINK_LIMIT_PER_IP"] == "${AUTH_LINK_LIMIT_PER_IP:-20}"
    assert env["AUTH_EXCHANGE_LIMIT_PER_IP"] == "${AUTH_EXCHANGE_LIMIT_PER_IP:-30}"
    assert "AUTH_LINK_LIMIT_PER_EMAIL" not in env


@pytest.mark.unit
def test_the_ci_e2e_stack_raises_only_the_per_ip_sign_in_limits() -> None:
    from test_compose import REPO_ROOT

    ci = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
    steps = ci["jobs"]["e2e"]["steps"]
    start = next(s for s in steps if s.get("name") == "Start the full stack")
    env = start.get("env", {})
    assert int(env["AUTH_LINK_LIMIT_PER_IP"]) >= 500
    assert int(env["AUTH_EXCHANGE_LIMIT_PER_IP"]) >= 500
    assert "AUTH_LINK_LIMIT_PER_EMAIL" not in env
