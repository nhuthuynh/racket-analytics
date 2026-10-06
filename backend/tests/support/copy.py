"""API error codes -> the exact copy the user sees (docs/design/flows-sprint-01.md).

api-sprint-01 §1.1: the FE maps ``code`` and ``fields[].code`` to the copy, and the server
``message`` stays generic. API-level scenario steps assert the code whose copy is the Gherkin
string; the browser specs assert the copy itself. One table, so the two cannot drift.
"""

from __future__ import annotations

from typing import Any

ERROR_COPY = {
    "link_expired": "This link has expired",
    "not_a_video": "This file is not a video we can read",
    "unsupported_video": "This file is not a video we can read",
    "video_too_large": "Videos must be 10 GB or smaller",
    "too_large": "Videos must be 10 GB or smaller",
    "too_long": "Videos must be 2 hours 30 minutes or shorter",
    "upload_expired": "This upload expired",
}
FIELD_COPY = {
    "side_needs_two_players": "Each side needs two players",
    "side_needs_one_player": "Each side needs one player",
    "choose_one_me": 'Choose one player as "me"',
    "format_required": "Select doubles or singles",
    "played_on_in_future": "The date must be today or in the past",
    "scoring_system_unavailable": "It becomes available once the rules are verified",
}
ACCEPTED_LINK_REQUEST = "Check your email"  # A-02 after a 202


def error_code(response: Any) -> str:
    return str(response.json()["error"]["code"])


def field_messages(response: Any) -> list[str]:
    fields = response.json()["error"].get("fields") or []
    return [FIELD_COPY.get(f["code"], f["code"]) for f in fields]
