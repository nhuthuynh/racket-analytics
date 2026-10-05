"""The Sprint 2 API shapes the live harness relies on (goal scorecard §4.0, G02-01..G02-04).

ASSUMPTIONS, NOT YET THE CONTRACT. They follow `docs/architecture/match-aggregate.md` §3-§5
(commands, If-Match version, projection, 409 `stale_match`). The principal-engineer writes the
real contract in `docs/architecture/api-sprint-02.md` (sprint-02 §4, due D2). If it differs,
the principal-engineer changes THIS file in the same commit, and the method author dry-runs
G02-01..G02-04 again before handover (ADR 0033 rule 2; decision-log row). No other harness
file hard-codes a Sprint 2 route or field.
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
}

# Body of start_game: the first serving side of the game (ST-021 explicit input, FR-045).
START_GAME_BODY = {"first_serving_side": "A", "ends_switched": False}
# Optimistic lock: the client sends the aggregate version it last saw (IT-02-04).
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
# Error codes (409 / 422 bodies carry {"code": ...}).
STALE, NOT_READY, INVALID_OUTCOME = "stale_match", "match_not_ready", "invalid_outcome"


def path(name: str, **ids: str) -> tuple[str, str]:
    method, template = ROUTES[name]
    return method, template.format(**ids)
