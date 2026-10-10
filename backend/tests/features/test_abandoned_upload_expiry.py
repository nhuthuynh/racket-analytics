"""API binding of tests/features/abandoned_upload_expiry.feature (ST-038; FR-024, NFR-066 d,
ADR 0006). The clock is injected as in IT-03-09: the upload's stored times are moved back, then
one purge pass runs (``purge --once``), which is what happens in the hours the Given names.
"Not listed": the match's entry in ``GET /matches`` offers no upload to resume. "Cannot be
resumed": HEAD and PATCH on the upload answer 404 or 410 (api-sprint-01 §5.2, sprint-03 §4).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from pytest_bdd import given, scenario, then, when

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support import tus
from tests.support.api import ApiDriver
from tests.support.paths import SYNTHETIC_CLIP

FEATURE = "abandoned_upload_expiry.feature"
CHUNK = 1024 * 1024


@scenario(FEATURE, "Upload never finished")
def test_upload_never_finished() -> None:
    pass


@scenario(FEATURE, "Upload finished in time")
def test_upload_finished_in_time() -> None:
    pass


@pytest.fixture
def ctx(api: ApiDriver, committed_db: Any) -> dict[str, Any]:
    return {"api": api, "db": committed_db}


def _move_back(db: Any, match_id: str, created: timedelta, updated: timedelta) -> None:
    with db.begin() as conn:
        conn.execute(
            sa.text(
                "UPDATE upload_sessions SET created_at = created_at - :c, "
                "updated_at = updated_at - :u WHERE match_id::text = :m"
            ),
            {"c": created, "u": updated, "m": match_id},
        )
        conn.execute(
            sa.text(
                "UPDATE media_assets SET created_at = created_at - :u WHERE match_id::text = :m"
            ),
            {"u": updated, "m": match_id},
        )


@given("Ivy started an upload 25 hours ago and never finished it")
def never_finished(ctx: dict[str, Any]) -> None:
    api = ctx["api"]
    client = api.as_user("ivy")
    ctx["match"] = api.run(sb.create_doubles(client, "Abandoned upload"))
    data = SYNTHETIC_CLIP.read_bytes()
    ctx["upload"] = api.run(tus.start(client, ctx["match"], len(data)))
    response = api.run(tus.patch(client, ctx["upload"], 0, data[:CHUNK]))
    assert response.status_code == 204, response.text
    listed = api.request("ivy", "GET", f"/matches/{ctx['match']}").json()
    assert listed["upload"], "positive control: the unfinished upload is offered before expiry"
    _move_back(ctx["db"], ctx["match"], timedelta(hours=25), timedelta(hours=25))
    st.run_purge_once()


@given("Ivy started an upload 23 hours ago and finished it 1 hour later")
def finished_in_time(ctx: dict[str, Any]) -> None:
    api = ctx["api"]
    ctx["match"] = api.run(sb.create_doubles(api.as_user("ivy"), "Finished upload"))
    api.run(sb.receive_video(api.as_user("ivy"), ctx["match"]))
    ctx["keys"] = st.object_keys_of(ctx["db"], ctx["match"])
    assert ctx["keys"], "positive control: the video is stored"
    _move_back(ctx["db"], ctx["match"], timedelta(hours=23), timedelta(hours=22))
    st.run_purge_once()


@when("she opens her matches list")
def opens_list(ctx: dict[str, Any]) -> None:
    response = st.request(ctx["api"], "ivy", "matches")
    assert response.status_code == 200, response.text
    body = response.json()
    items = body["items"] if isinstance(body, dict) else body
    ctx["item"] = next(i for i in items if i["id"] == ctx["match"])


@then("the partial upload is not listed")
def not_listed(ctx: dict[str, Any]) -> None:
    assert ctx["item"]["upload"] in (None, {}), f"still offered: {ctx['item']['upload']}"


@then("it cannot be resumed")
def cannot_resume(ctx: dict[str, Any]) -> None:
    api, upload = ctx["api"], ctx["upload"]
    client = api.as_user("ivy")
    assert api.run(tus.head(client, upload)).status_code in (404, 410)
    assert api.run(tus.patch(client, upload, CHUNK, b"x" * 16)).status_code in (404, 410)


@then("the match is listed with its video")
def listed_with_video(ctx: dict[str, Any]) -> None:
    assert ctx["item"]["status"] == "video_received", ctx["item"]
    assert ctx["item"]["upload"] is None
    assert st.keys_still_stored(ctx["keys"]) == ctx["keys"]
