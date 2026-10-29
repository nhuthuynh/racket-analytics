"""env.example -> Compose parity (SRE-VERIFY04R3-02; Sprint 4 retro C2/C3, VERIFY-04-r3).

VERIFY-04-r3 found that infra/env.example listed the Sprint 4 settings (FEATURE_*, retention,
quotas, ...) but infra/compose.yaml forwarded none of them, so ``make up`` with a flag on in
infra/.env still ran with the flag off. This check makes that a test failure:

1. every setting in env.example is used by compose.yaml (``${NAME``), or is listed in
   ``HOST_ONLY`` with the reason no Compose service reads it;
2. every env.example setting the backend ``Settings`` reads reaches each service that runs it
   (``SETTINGS_READERS``, narrowed only by ``SCOPED``), forwarded as ``${NAME...}``;
3. a Compose fallback (``${NAME:-x}``) equals the env.example value, except ``SAFE_FALLBACKS``.

Pure functions of three paths, so a test can plant a broken copy and see it fail.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

# Services whose process builds racket.platform.settings.Settings from its environment.
SETTINGS_READERS = ("api", "worker", "mailer", "purge")
# Backend-image services that do not build Settings (only DATABASE_URL).
NON_READERS = {"migrate": "applies Alembic migrations with DATABASE_URL only"}
# Settings read by fewer services, on purpose (least privilege, ST-013/ST-042, C-18).
SCOPED: dict[str, tuple[str, ...]] = {
    "PUBLIC_WEB_ORIGIN": ("api", "mailer"),  # sign-in link (ADR 0027)
    "MAIL_FROM": ("api", "mailer"),
    "AUTH_EMAIL_KEY": ("api", "mailer"),
    "ALLOWED_ORIGINS": ("api",),  # origin check on HTTP requests (C-18)
    "API_PUBLIC_PATH_PREFIX": ("api",),  # tus Location header (R1-02)
    # The app's media key; the worker gets its own key under the same name (ST-042) and the
    # mailer none (SEC-R5-S1-01).
    "S3_ACCESS_KEY_ID": ("api", "purge"),
    "S3_SECRET_ACCESS_KEY": ("api", "purge"),
}
# env.example settings no Compose service reads.
HOST_ONLY = {
    "BILLING_BUDGET_LLM_PROVIDER_USD": "infra/observability/billing_budgets.py (host/collector)",
    "BILLING_BUDGET_OBJECT_STORE_USD": "infra/observability/billing_budgets.py (host/collector)",
    "BILLING_ALERT_RECEIVER_URL_FILE": "Alertmanager url_file; no Compose service (ST-073)",
}
# Compose falls back to the safe value when infra/.env omits it (ST-006).
SAFE_FALLBACKS = {"DEV_IDENTITY_ENABLED": "false"}

_SETTINGS_READ = re.compile(r'(?:env\.get|required|optional|integer|boolean)\(\s*"([A-Z0-9_]+)"')
_FALLBACK = re.compile(r"^\$\{(?P<name>[A-Z0-9_]+):-(?P<value>[^}]*)\}$")


def env_example(path: Path) -> dict[str, str]:
    lines = (ln.strip() for ln in path.read_text().splitlines())
    return dict(ln.split("=", 1) for ln in lines if ln and not ln.startswith("#") and "=" in ln)


def settings_names(path: Path) -> set[str]:
    return set(_SETTINGS_READ.findall(path.read_text()))


def service_env(compose: dict, service: str) -> dict[str, str]:
    env = compose["services"][service].get("environment") or {}
    if isinstance(env, list):
        env = dict(e.split("=", 1) for e in env)
    return {k: str(v) for k, v in env.items()}


def check(env_path: Path, compose_path: Path, settings_path: Path) -> list[str]:
    """Every parity problem, one line each naming the setting (and service); [] when none."""
    example = env_example(env_path)
    text = compose_path.read_text()
    compose = yaml.safe_load(text)
    read = settings_names(settings_path)
    problems: list[str] = []
    for name in sorted(example):
        if name in HOST_ONLY:
            if name in read:
                problems.append(f"{name}: in HOST_ONLY but the backend Settings reads it")
        elif "${" + name not in text:
            problems.append(f"{name}: in env.example but not forwarded to any Compose service")
    for name in sorted((read & example.keys()) - HOST_ONLY.keys()):  # reported once above
        for service in SCOPED.get(name, SETTINGS_READERS):
            value = service_env(compose, service).get(name, "")
            if "${" + name not in value:
                problems.append(f"{name}: read by Settings but not forwarded to {service}")
    for service in compose["services"]:
        for name, value in service_env(compose, service).items():
            m = _FALLBACK.match(value)
            if m and m["name"] in example:
                want = SAFE_FALLBACKS.get(m["name"], example[m["name"]])
                if m["value"] != want:
                    problems.append(
                        f"{name} on {service}: Compose fallback {m['value']!r} differs from "
                        f"env.example {want!r}"
                    )
    return list(dict.fromkeys(problems))  # a merged anchor repeats a fallback per service
