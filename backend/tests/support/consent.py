"""Helpers for the FR-009 training-data consent tests (ST-070; api-sprint-04 §6; SEC-4 T4-CS).

The app is built after ``FEATURE_TRAINING_CONSENT`` is set (the flag is read at start-up) on the
committed database, because the label-set build runs as its own entry point
(``racket.dataset.build_label_set:main``) with its own session, as an operator runs it in the
``api`` container. Rows are read with plain SQL: the tests never import the product's tables.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import contract
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.contract import Seam

CONSENT = "/me/training-consent"
BUILD_MAIN = Seam(
    "racket.dataset.build_label_set:main",
    "ST-070",
    "main(argv) -> int: builds the next label set, prints its manifest JSON on stdout; "
    "['--out', <path>] also writes it there and refuses an existing file (frozen versions are "
    "never edited); exit 1 and no output when the consent lookup fails (T4-CS-1)",
)


def build_api(monkeypatch: pytest.MonkeyPatch, *, on: bool) -> ApiDriver:
    monkeypatch.setenv("FEATURE_TRAINING_CONSENT", "true" if on else "false")
    return ApiDriver(contract.APP_FACTORY.load()())


def tagged_match(api: ApiDriver, user: str, title: str) -> str:
    """A doubles match with its video received and the worked example tagged (Quick Tag
    rallies are the player's corrections, the training data of FR-009)."""
    return st.tagged_example(api, user, title)


def put_opt_in(api: ApiDriver, user: str, value: Any) -> httpx.Response:
    return api.request(user, "PUT", CONSENT, json={"opt_in": value})


def account_id(api: ApiDriver, user: str) -> str:
    response = api.request(user, "GET", "/me")
    assert response.status_code == 200, response.text
    return str(response.json()["id"])


def record_team_consent(match_id: str, reference: str = "TEAM-FORM-070") -> None:
    """The FR-150 team-held consent record, written through the operator CLI (ST-052b)."""
    rc = st.LABELLER_ADMIN.load()(["consent", "--match", match_id, "--record", reference])
    assert rc == 0, f"admin consent exit {rc}"


def build(*options: str) -> tuple[int, str]:
    """Run one label-set build in-process; (exit code, stdout)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc: int = BUILD_MAIN.load()(list(options))
    return rc, out.getvalue()


def built_match_ids(stdout: str) -> list[str]:
    manifest = json.loads(stdout)
    return [str(entry["match_id"]) for entry in manifest["matches"]]


def build_ids(*options: str) -> list[str]:
    rc, stdout = build(*options)
    assert rc == 0, f"label-set build exit {rc}: {stdout[:300]}"
    return built_match_ids(stdout)


def build_to(path: Path) -> list[str]:
    ids = build_ids("--out", str(path))
    assert built_match_ids(path.read_text(encoding="utf-8")) == ids
    return ids


def consent_events(engine: Any, account: str) -> list[bool]:
    """The account's ``training_consent_events`` (``opt_in`` in time order)."""
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT opt_in FROM training_consent_events WHERE account_id::text = :a "
                "ORDER BY changed_at, id"
            ),
            {"a": account},
        ).scalars()
        return [bool(v) for v in rows]


def consent_rows(engine: Any, account: str) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text(
                    "SELECT (SELECT count(*) FROM training_consent_events WHERE account_id::text"
                    " = :a) + (SELECT count(*) FROM training_consents WHERE account_id::text = :a)"
                ),
                {"a": account},
            ).scalar_one()
        )
