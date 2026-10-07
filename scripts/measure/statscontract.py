"""The Sprint 3 API shapes the live harness relies on (goal scorecard G03-01..G03-05).

**Source of truth: `docs/architecture/api-sprint-03.md`** (principal-engineer, PE-1, Accepted
for build 2026-10-07). This file mirrors it: a change there changes THIS file in the same
commit, and the method authors dry-run G03-01..G03-05 again before handover (ADR 0033 rule 2).
No other harness file hard-codes a Sprint 3 route or field.
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

# Stats body (api-sprint-03 §2.1): {"match_id", "sheet_version", "rules_version",
#   "metric_def_version", "unofficial": bool, "label": str, "low_sample_rule": {...},
#   "metrics": {"AN-01": {"entry": {...}, "A": {...}, "B": {...}}, ...}}; per-side fields are
# statslib.COMPARED. Only coach-reviewed or verified entries appear (FR-102).
METRICS_KEY = "metrics"
DEF_VERSION_KEY = "metric_def_version"
RULES_VERSION_KEY = "rules_version"
# Evidence body (api-sprint-03 §3.1): {"metric_id", "side", "total": n, "sheet_version",
#   "items": [{"number", "rally_id", "game", "start_ms", "end_ms"}...], "next_cursor"}
# (FR-103: limit 1-10, default 10; "see all n" = total, paged with cursor). An unpublished
# metric id is 404; a bad side, limit or cursor is 422.
EVIDENCE_ITEMS, EVIDENCE_TOTAL, EVIDENCE_RALLY_ID = "items", "total", "rally_id"
# Deletion (api-sprint-03 §4): DELETE answers 202 {"deleted": true, "purge_due_by"} (hidden
# now, purge to come); a second DELETE of the match is 404; afterwards every route of the match
# answers 404 (FR-006); DELETE /me signs out every session of the account (FR-007) and the
# address signs in again to a new, empty account (PM-1 default).
DELETE_OK = (202,)
# Purge job (api-sprint-03 §4.4; ADR 0038, 0042): exit 0 done, 1 an item failed (retried), 2
# usage. Run once on the live stack in the `purge` Compose service (never `worker`, ST-042).
PURGE_ONCE = "python -m racket.platform.purge --once"
PURGE_SERVICE = "purge"
PURGE_SCHEDULE_VAR = "PURGE_INTERVAL_S"  # default 86400, refused above 86400 (NFR-066 c)
# Delete-confirmation guard (DES FR-UX-90): the client sends this exact object; anything else
# is 422 validation_failed with confirm/confirmation_required.
CONFIRM_BODY = {"confirm": "delete"}
# Full Tag (api-sprint-03 §5): non-labeller -> 404 on every route; labeller without a consent
# record -> 409 no_consent; invalid label -> 422 invalid_label. Admin CLI (§5.5):
# python -m racket.dataset.admin grant-labeller --account <id> | consent --match <id> --record <ref>
LABEL_ROUTES = {
    "label_match": ("GET", "/label/matches/{match_id}"),
    "label_events": ("POST", "/label/matches/{match_id}/events"),
    "label_export": ("GET", "/label/matches/{match_id}/export"),
}
LABELLER_ADMIN = "python -m racket.dataset.admin"


def path(name: str, **ids: str) -> tuple[str, str]:
    method, template = ROUTES[name]
    return method, template.format(**ids)
