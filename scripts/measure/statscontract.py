"""The Sprint 3 API shapes the live harness relies on (goal scorecard G03-01..G03-05).

**Assumptions until `docs/architecture/api-sprint-03.md` is written and reviewed** (principal-
engineer, sprint-03 §4, task PE-1 on D1). The contract is then the source of truth: a change
there changes THIS file in the same commit, and the method authors dry-run G03-01..G03-05 again
before handover (ADR 0033 rule 2). No other harness file hard-codes a Sprint 3 route or field.
"""

from __future__ import annotations

ROUTES = {
    "stats": ("GET", "/matches/{match_id}/stats"),
    "evidence": ("GET", "/matches/{match_id}/stats/{metric_id}/evidence?side={side}&limit=10"),
    "match": ("GET", "/matches/{match_id}"),
    "matches": ("GET", "/matches"),
    "delete_match": ("DELETE", "/matches/{match_id}"),
    "delete_account": ("DELETE", "/me"),
    "me": ("GET", "/me"),
}

# Stats body: {"rules_version", "metric_def_version", "unofficial": bool, "label": str,
#              "metrics": {"AN-01": {"A": {...}, "B": {...}}, ...}}; per-side fields are
# statslib.COMPARED. Only coach-reviewed or verified entries appear (FR-102).
METRICS_KEY = "metrics"
DEF_VERSION_KEY = "metric_def_version"
RULES_VERSION_KEY = "rules_version"
# Evidence body: {"total": n, "items": [{"number": <match-wide rally number>, "rally_id",
#                 "game", "start_ms"}...]} (FR-103: at most 10 items, "see all n" = total).
EVIDENCE_ITEMS, EVIDENCE_TOTAL, EVIDENCE_RALLY_ID = "items", "total", "rally_id"
# Deletion: DELETE answers 202 (hidden now, purge queued) or 204; afterwards every route of the
# match answers 404 (FR-006); DELETE /me signs out every session of the account (FR-007).
DELETE_OK = (202, 204)
# Purge job, run once on the live stack (worker CLI; the PE names it in api-sprint-03 §deletion).
PURGE_ONCE = "python -m racket.platform.purge --once"
# Delete-confirmation guard (DES FR-UX-90): the client sends the typed confirmation.
CONFIRM_BODY = {"confirm": "delete"}


def path(name: str, **ids: str) -> tuple[str, str]:
    method, template = ROUTES[name]
    return method, template.format(**ids)
