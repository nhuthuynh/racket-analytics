"""IT-03-13 (ST-050, ST-051, ST-052; NFR-057, NFR-069): deletion, purge and labelling log lines
carry ids and the pseudonymous account id only: never an address, a title, a nickname, a
consent reference or a label value.

Positive control: a deletion line, a purge line and an account-deletion line exist and carry
``match_id`` / ``user_id``. Event names are matched by stem (``delet``, ``purg``) until PE-3
names them. The labelling half joins when ST-052 lands (its own test, same rules).
Written red first (QA-ACC-3): ``red_until`` ST-050.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.support import logscan
from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.red_until(story="ST-050")]

TITLE = "Secret Saturday title"
NICKNAMES = ("Ivy", "Dana", "Carlos", "Sam")
CONSENT_REF = "CONSENT-TEAM-SYNTHETIC-777"


def _records(capfd: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    out, err = capfd.readouterr()
    return [json.loads(line) for line in (out + err).splitlines() if line.startswith("{")]


def _check_clean(records: list[dict[str, Any]]) -> None:
    for record in records:
        text = json.dumps(record)
        assert TITLE not in text, text
        assert not any(f'"{n}"' in text for n in NICKNAMES), text
        assert "@" not in text, text
        assert CONSENT_REF not in text, text
    lines = [json.dumps(r) for r in records]
    assert logscan.scan(lines, NICKNAMES) == []


def test_it_03_13_match_deletion_and_purge_lines_hold_ids_only(
    api: ApiDriver, capfd: pytest.CaptureFixture[str]
) -> None:
    match_id = st.tagged_example(api, "ivy", TITLE)
    capfd.readouterr()
    assert st.delete_match(api, "ivy", match_id).status_code in st.statscontract.DELETE_OK
    st.run_purge_once()
    records = _records(capfd)
    deleted = [r for r in records if "delet" in str(r.get("event", "")).lower()]
    purged = [r for r in records if "purg" in str(r.get("event", "")).lower()]
    assert deleted, "no deletion line (audit by pseudonymous id, NFR-057)"
    assert purged, "no purge line"
    assert any(r.get("match_id") == match_id for r in deleted)
    assert all(r.get("user_id") for r in deleted), deleted
    _check_clean(records)


def test_it_03_13_account_deletion_lines_hold_ids_only(
    api: ApiDriver, capfd: pytest.CaptureFixture[str]
) -> None:
    st.tagged_example(api, "ivy", TITLE)
    me = st.me_id(api, "ivy")
    capfd.readouterr()
    assert st.delete_account(api, "ivy").status_code in st.statscontract.DELETE_OK
    st.run_purge_once()
    records = _records(capfd)
    account = [r for r in records if "account" in str(r.get("event", "")).lower()]
    assert account, "no account-deletion line"
    assert any(r.get("user_id") == me for r in account), account
    _check_clean(records)
