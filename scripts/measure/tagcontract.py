"""The Sprint 2 API shapes the live harness relies on (goal scorecard §4.0, G02-01..G02-04).

A mirror of `docs/architecture/api-sprint-02.md` (Accepted, design review D1, 2026-10-06).
The contract is the source of truth: a change there changes THIS file in the same commit, and
the method author dry-runs G02-01..G02-04 again before handover (ADR 0033 rule 2). No other
harness file hard-codes a Sprint 2 route or field.
"""

from __future__ import annotations

ROUTES = {
    "start_game": ("POST", "/matches/{match_id}/games"),
    "tag": ("POST", "/matches/{match_id}/rallies"),
    "sheet": ("GET", "/matches/{match_id}/score-sheet"),
    "correct": ("PATCH", "/matches/{match_id}/rallies/{rally_id}"),
    "undo": ("POST", "/matches/{match_id}/undo"),
    "history": ("GET", "/matches/{match_id}/corrections"),
    "media": ("GET", "/matches/{match_id}/rallies/{rally_id}/media"),
    "video": ("GET", "/matches/{match_id}/video"),
    "resolve": ("POST", "/matches/{match_id}/rallies/{rally_id}/resolution"),
}

# Body of start_game: the first serving side of the game (ST-021 explicit input, FR-045).
START_GAME_BODY = {"first_serving_side": "A", "ends_switched": False}
# Optimistic lock: the client sends the aggregate version it last saw (IT-02-04); the API
# accepts 3, "3" or W/"3" and answers ETag: "<version>" (api-sprint-02 §1.2).
VERSION_HEADER = "If-Match"
# Command responses: {"version": int, "sheet": <sheet>}; tag responses add "rally_id".
VERSION_KEY, SHEET_KEY, RALLY_ID_KEY = "version", "sheet", "rally_id"
# Sheet: {"rules_version": str, "unofficial": bool, "label": str, "rows": [row...]};
# row fields are taglib.ROW_FIELDS plus "rally_id" and "corrected_by_user".
CORRECTED_KEY = "corrected_by_user"
# History: {"items": [{"kind", "rally_id", "field", "old_value", "new_value", "undoes"}...]}
HISTORY_ITEMS = "items"
# Media: {"url": str, "expires_in_s": int, "start_ms": int}
MEDIA_URL, MEDIA_TTL, MEDIA_START = "url", "expires_in_s", "start_ms"
# Error codes, read from the api-sprint-00 §3 envelope {"error": {"code", ...}} (§1.1).
STALE, NOT_READY, INVALID_OUTCOME = "stale_match", "match_not_ready", "invalid_outcome"


def path(name: str, **ids: str) -> tuple[str, str]:
    method, template = ROUTES[name]
    return method, template.format(**ids)
