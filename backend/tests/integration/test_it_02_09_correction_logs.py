"""IT-02-09 (ST-031; NFR-069, NFR-057): correction, undo and tag log lines carry ``match_id``
and the pseudonymous account id only: no title, nickname, address, rally values or token.

Positive control: the lines exist and carry ``match_id`` and ``user_id``.
"""

from __future__ import annotations

import json

import pytest

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

TITLE = "Secret Saturday title"
NICKNAMES = ("Ivy", "Dana", "Carlos", "Sam")
EVENTS = {"match.rally_tagged", "match.rally_corrected", "match.undone", "match.game_started"}


def test_it_02_09_scorebook_log_lines_hold_ids_only(
    api: ApiDriver, capfd: pytest.CaptureFixture[str]
) -> None:
    capfd.readouterr()
    match_id = sb.ready_tagged_match(api, "ivy", title=TITLE)
    ivy = api.as_user("ivy")
    rally_2 = api.run(sb.sheet(ivy, match_id)).json()["rows"][1]["rally_id"]
    version = api.run(sb.version_of(ivy, match_id))
    corrected = api.run(
        sb.command(ivy, "correct", version=version, body={"field": "ending", "value": "winner"},
                   match_id=match_id, rally_id=rally_2)
    )  # fmt: skip
    assert corrected.status_code == 200
    undone = api.run(
        sb.command(ivy, "undo", version=corrected.json()["version"], match_id=match_id)
    )
    assert undone.status_code == 200
    out, err = capfd.readouterr()

    records = [json.loads(line) for line in (out + err).splitlines() if line.startswith("{")]
    scorebook = [r for r in records if r.get("event") in EVENTS]
    assert {r["event"] for r in scorebook} == EVENTS, "a scorebook event was not logged"
    for record in scorebook:
        assert record["match_id"] == match_id
        assert record["user_id"], record  # pseudonymous account id (a UUID), never a name
        text = json.dumps(record)
        assert TITLE not in text
        assert not any(f'"{n}"' in text for n in NICKNAMES), text
        assert "@" not in text
        assert "forced_error" not in text  # no rally values (also matches unforced_error)
    assert all(TITLE not in json.dumps(r) for r in records), "the title reached a log line"
