"""R1-07: api-sprint-00 §5.2/§7 as amended -- ``GET /matches/{id}/media`` is 204 (no body,
``Cache-Control: no-store``) while the owner's video is not probed yet, and 404 for anyone else.
"""

from __future__ import annotations

from typing import Any

from tests.support.api import ApiDriver
from tests.support.flows import create_match


def test_not_probed_media_is_404_for_others_and_204_no_store_for_the_owner(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Not probed"))

    other = api.request("carlos", "GET", f"/matches/{match_id}/media")
    owner: Any = api.request("ivy", "GET", f"/matches/{match_id}/media")

    assert other.status_code == 404
    assert owner.status_code == 204
    assert owner.content == b""
    assert owner.headers["Cache-Control"] == "no-store"
