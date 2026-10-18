"""IT-04-08 consent and the label set (ST-070; FR-009; FR-150; OQ-06, ADR 0023; api-sprint-04 §6;
context map R9; SEC-4 T4-CS-1..T4-CS-4): API <-> DB <-> label-set build entry point.

Negative cases first: with ``FEATURE_TRAINING_CONSENT`` off the routes are 404 and the build
keeps the FR-150 rule (only matches with a team-held consent record); with it on, no consent
row means not consented, another account's opt-in never includes Ivy's match, a team-held
record alone no longer includes it, and a failing consent lookup aborts the build with no
output. Then the audit trail (on, on, off -> 2 events), opt-in includes the match, a revoke
excludes it from the next build while the frozen earlier build is not edited."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.support import consent as cs
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.contract import Seam

CONSENT_PORT = Seam(
    "racket.players.public:training_opted_in",
    "ST-070",
    "training_opted_in(session, account_ids) -> set[UUID]: the live accounts that opted in",
)


@pytest.fixture
def on(monkeypatch: pytest.MonkeyPatch, committed_db: Any) -> Iterator[ApiDriver]:
    driver = cs.build_api(monkeypatch, on=True)
    yield driver
    driver.close()


@pytest.fixture
def off(monkeypatch: pytest.MonkeyPatch, committed_db: Any) -> Iterator[ApiDriver]:
    driver = cs.build_api(monkeypatch, on=False)
    yield driver
    driver.close()


def _error(response: Any) -> tuple[int, str, list[tuple[Any, Any]]]:
    body = response.json()["error"]
    fields = [(f.get("field"), f.get("code")) for f in body.get("fields") or []]
    return response.status_code, body["code"], fields


# ------------------------------------------------------------------ flag off (negative first)
def test_it_04_08_flag_off_routes_404_and_the_build_keeps_the_team_record_rule(
    off: ApiDriver,
) -> None:
    plain = cs.tagged_match(off, "ivy", "IT-04-08 off plain")
    recorded = cs.tagged_match(off, "carlos", "IT-04-08 off recorded")
    cs.record_team_consent(recorded)
    assert off.request("ivy", "GET", cs.CONSENT).status_code == 404
    assert cs.put_opt_in(off, "ivy", True).status_code == 404
    rc, stdout = cs.build()
    assert rc == 0, stdout
    manifest = json.loads(stdout)
    assert manifest["consent_rule"] == "team_record"
    assert cs.built_match_ids(stdout) == [recorded]
    assert plain not in stdout


def test_it_04_08_the_setting_needs_a_session_and_a_closed_body(
    on: ApiDriver, committed_db: Any
) -> None:
    assert on.request("anonymous", "GET", cs.CONSENT).status_code == 401
    assert cs.put_opt_in(on, "anonymous", True).status_code == 401
    bad = [
        ({}, ("opt_in", "required")),
        ({"opt_in": "true"}, ("opt_in", "invalid")),
        ({"opt_in": 1}, ("opt_in", "invalid")),
        ({"opt_in": None}, ("opt_in", "invalid")),
        ({"opt_in": True, "account_id": "x"}, (None, "unknown_field")),
        ([True], (None, "invalid")),
    ]
    for body, field in bad:
        response = on.request("ivy", "PUT", cs.CONSENT, json=body)
        assert _error(response) == (422, "validation_failed", [field]), (body, response.text)
    got = on.request("ivy", "GET", cs.CONSENT)
    assert got.status_code == 200
    assert got.json() == {"opt_in": False, "changed_at": None}
    assert got.headers["Cache-Control"] == "no-store"
    assert cs.consent_rows(committed_db, cs.account_id(on, "ivy")) == 0


def test_it_04_08_no_opt_in_and_another_accounts_opt_in_leave_my_match_out(
    on: ApiDriver,
) -> None:
    """T4-CS-1 (no row = no), T4-CS-4 (the match owner's consent, never another account's) and
    the flag-on rule (a team-held record alone does not include a match)."""
    ivy = cs.tagged_match(on, "ivy", "IT-04-08 ivy")
    carlos = cs.tagged_match(on, "carlos", "IT-04-08 carlos")
    cs.record_team_consent(ivy)
    assert cs.build_ids() == []
    assert cs.put_opt_in(on, "carlos", True).status_code == 200
    rc, stdout = cs.build()
    assert rc == 0, stdout
    assert json.loads(stdout)["consent_rule"] == "owner_opt_in"
    assert cs.built_match_ids(stdout) == [carlos]
    assert ivy not in stdout


def test_it_04_08_a_failing_consent_lookup_aborts_the_build_with_no_output(
    on: ApiDriver, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T4-CS-1: fail closed; no partial set, nothing written."""
    cs.tagged_match(on, "ivy", "IT-04-08 lookup failure")
    assert cs.put_opt_in(on, "ivy", True).status_code == 200
    module = CONSENT_PORT.load().__module__

    def failing(*_: Any, **__: Any) -> Any:
        raise ConnectionError("injected consent lookup failure (IT-04-08)")

    monkeypatch.setattr(f"{module}.training_opted_in", failing)
    out = tmp_path / "label-set.json"
    rc, stdout = cs.build("--out", str(out))
    assert rc == 1
    assert stdout == ""
    assert not out.exists()


# ------------------------------------------------------------------ audit trail
def test_it_04_08_each_change_writes_one_event_and_the_same_value_writes_nothing(
    on: ApiDriver, committed_db: Any
) -> None:
    """T4-CS-3: on, on, off -> 2 events."""
    account = cs.account_id(on, "ivy")
    first = cs.put_opt_in(on, "ivy", True)
    assert first.status_code == 200, first.text
    assert first.json()["opt_in"] is True
    changed_at = first.json()["changed_at"]
    assert isinstance(changed_at, str)
    assert changed_at.endswith("Z")
    again = cs.put_opt_in(on, "ivy", True)
    assert again.status_code == 200
    assert again.json() == {"opt_in": True, "changed_at": changed_at}
    off_again = cs.put_opt_in(on, "ivy", False)
    assert off_again.status_code == 200
    assert off_again.json()["opt_in"] is False
    assert cs.consent_events(committed_db, account) == [True, False]
    assert on.request("ivy", "GET", cs.CONSENT).json() == off_again.json()
    assert cs.consent_events(committed_db, cs.account_id(on, "carlos")) == []


# ------------------------------------------------------------------ opt in, revoke, frozen
def test_it_04_08_opt_in_includes_revoke_excludes_from_the_next_build_v1_unchanged(
    on: ApiDriver, tmp_path: Path
) -> None:
    """T4-CS-2: build v1 (included), revoke, build v2 (excluded); v1 is not edited, and a build
    never writes over an existing set file."""
    match_id = cs.tagged_match(on, "ivy", "IT-04-08 revoke")
    assert cs.put_opt_in(on, "ivy", True).status_code == 200
    v1 = tmp_path / "label-set-v1.json"
    assert cs.build_to(v1) == [match_id]
    frozen = v1.read_bytes()
    entry = json.loads(frozen)["matches"][0]
    assert entry["rallies"] == len(st.WORKED_EXAMPLE)
    assert set(entry) == {"match_id", "rallies", "full_tag_labels"}  # no owner id, no email

    assert cs.put_opt_in(on, "ivy", False).status_code == 200
    v2 = tmp_path / "label-set-v2.json"
    assert cs.build_to(v2) == []
    assert v1.read_bytes() == frozen
    rc, _ = cs.build("--out", str(v1))
    assert rc == 2
    assert v1.read_bytes() == frozen


def test_it_04_08_a_deleted_account_leaves_the_set_and_its_consent_rows_go(
    on: ApiDriver, committed_db: Any
) -> None:
    match_id = cs.tagged_match(on, "ivy", "IT-04-08 deleted")
    account = cs.account_id(on, "ivy")
    assert cs.put_opt_in(on, "ivy", True).status_code == 200
    assert cs.build_ids() == [match_id]
    method, url = st.statscontract.path("delete_account")
    deleted = on.request("ivy", method, url, json=st.statscontract.CONFIRM_BODY)
    assert deleted.status_code == 202, deleted.text
    assert cs.build_ids() == []
    st.run_purge_once()
    assert cs.consent_rows(committed_db, account) == 0
