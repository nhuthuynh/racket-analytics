# API contract: Sprint 3 (stats, evidence, deletion, Full Tag labelling)

- **Status:** Accepted for build (principal-engineer, 2026-10-07, Sprint 3 review round 1, PE-R1S3-02 / task PE-1). Written before the routes exist; it adopts the shapes the QA harness already assumed (`scripts/measure/statscontract.py`, `backend/tests/support/stats.py`) wherever they were sound, so the red-first tests keep working, and fixes what was open (status codes, error codes, pagination, the confirmation body, the label routes). Review: BE, FE, QA and security-privacy-engineer write comments as rows under "Design review D3 (api-sprint-03.md)" in `docs/sprints/03/review-rounds.md`; a change goes through the ticket PR of the story that needs it (ADR 0039) and changes `scripts/measure/statscontract.py` in the same commit (ADR 0033 rule 2).
- **Owner:** principal-engineer. **Domain designs:** `analytics-snapshots.md` (ST-046, ST-047), `deletion-and-purge.md` (ST-050, ST-051, ST-038), `backend/src/racket/dataset/full_tag.py` (ST-052 slice a). **Security:** SEC-1 threat notes are acceptance criteria of the stories (ADR 0022 rule 4).
- **Stories:** ST-046, ST-047 (API), ST-050 (API), ST-051 (API), ST-038, ST-052 (b, c).
- **Builds on:** `api-sprint-00.md`, `api-sprint-01.md`, `api-sprint-02.md`; all of it still holds: root path behind `/api`; `application/json`; UUIDv4 ids, a malformed id is 404; closed request schemas; the error envelope `{"error": {"code", "message", "support_ref", "fields"?}}` with fixed messages that never echo input; security headers; `Cache-Control: no-store`; the Origin check on state-changing requests; the session cookie.
- **Product-owner inputs:** ADR 0023 and `po-input-2026-10-05.md`: scoring presets stay PROVISIONAL-UNVERIFIED, so stats say "unofficial"; jurisdictions US + AU (NFR-070 open); the dev stack is HTTPS.

## 1. Conventions added

### 1.1 Ownership and deletion

Every route that names a match loads it through the owner filter, which also excludes deleted (tombstoned) matches: another account's match, an unknown id, a malformed id and a **deleted** match all give **404 `not_found`** with the same body (NFR-051; deletion-and-purge.md §3.1). The label routes add the labeller check before the owner filter (§5.1).

### 1.2 Pagination

Same as `GET …/corrections` (api-sprint-02 §2.2): `limit` and an opaque `cursor`; the response has `next_cursor` (`null` on the last page). An invalid `limit` or `cursor` is 422 `validation_failed` with `limit`/`invalid` or `cursor`/`invalid`.

## 2. Stats (ST-046; FR-100, FR-101, FR-102, FR-055)

### 2.1 `GET /matches/{match_id}/stats`

200, `Cache-Control: no-store`. Always current with the score sheet (read repair, analytics-snapshots.md §4.2). A match with no rallies (or no video yet) answers 200 with every published metric at n = 0.

Example: the coach's worked example (metric-dictionary §2, 14 rallies), AN-01 only, with AN-01 published.

```json
{"match_id": "…", "sheet_version": 15,
 "rules_version": "PROVISIONAL-UNVERIFIED", "metric_def_version": "0.1",
 "unofficial": true, "label": "unofficial scoring (rules not yet verified)",
 "low_sample_rule": {"max_interval_width": 0.3},
 "metrics": {
   "AN-01": {
     "entry": {"id": "AN-01", "version": "0.1", "name": "Rallies won on serve",
               "definition": "…plain words…", "unit": "proportion",
               "min_sample": {"unit": "rallies", "n": 20}, "status": "coach-reviewed"},
     "A": {"k": 4, "n": 7, "value": 0.5714, "ci_low": 0.2505, "ci_high": 0.8418, "low_sample": true},
     "B": {"k": 4, "n": 6, "value": 0.6667, "ci_low": 0.3, "ci_high": 0.9032, "low_sample": true}},
   "…": {}}}
```

- `metrics` holds **only** entries with status `coach-reviewed` or `verified` (FR-102). A draft or deprecated id appears nowhere in the body (IT-03-03). With no published entry, `metrics` is `{}` (the dashboard shows its empty state, not an error).
- `entry` is `MetricEntry.public()` of the dictionary version named by `metric_def_version`; `entry.min_sample` is the threshold the flag used (single source, ADR 0041). `min_sample` is `null` for a descriptive metric (AN-06), which is never flagged.
- `unofficial` is `true` and `label` the fixed text while the preset is unverified (ADR 0009, ADR 0023); same rule and text as the score sheet (api-sprint-02 §2.1).
- `low_sample_rule.max_interval_width` comes from the dictionary (ADR 0041); the card text is "low sample: n below {min_sample.n}, or the range is wider than {width × 100} points".
- **Per-side fields** (`A`, `B`; numbers rounded to 4 places; `value` and bounds `null` when n = 0):

| Metric | Fields |
|---|---|
| AN-01, AN-02 | `k`, `n`, `value`, `ci_low`, `ci_high`, `low_sample` |
| AN-03 | `points`, `turns`, `value`, `low_sample` |
| AN-04 | `count`, `games`, `value`, `by_player` (slot → count, slots only, never names), `player_not_tagged`, `low_sample` |
| AN-05 | `k`, `n`, `value`, `ci_low`, `ci_high`, `fault_type_not_tagged`, `low_sample` |
| AN-06 | `longest` (match-wide), `longest_by_game` (the longest run of that side in each game in scope, games in play order, 0 for a game without a run; dictionary AN-06, the value the coach defined), `histogram` (`"1"`, `"2"`, `"3"`, `"4"`, `"5+"`), `n`, `low_sample` (always `false`) |
| AN-07 | `n`, `counts` (`winner`, `unforced_error`, `forced_error`, `fault`), `shares` (per category `k`, `value`, `ci_low`, `ci_high`), `low_sample` |

  These are exactly `starter_stats()` (ST-044) without the `rallies` lists, which `…/evidence` serves; `backend/tests/unit/analytics/test_stats_contract_doc.py` fails when the domain output and this table differ (PE-R2S3-04, 2026-10-07: `longest_by_game` added after `fee4fa3`). The harness compares `statslib.COMPARED` keys only, and `COMPARED["AN-06"]` must hold `longest_by_game` (owner: senior-qa-engineer, QA-R2S3-01).
- Refusals: 401; 404 (§1.1). No other.

### 2.2 Read latency

NFR-010: p95 ≤ 300 ms, p99 ≤ 800 ms at 50 RPS (G03-05).

## 3. Evidence (ST-047; FR-103, FR-027)

### 3.1 `GET /matches/{match_id}/stats/{metric_id}/evidence?side=A|B&limit=10&cursor=…`

200, `Cache-Control: no-store`:

```json
{"metric_id": "AN-01", "side": "A", "total": 7, "sheet_version": 15,
 "items": [{"number": 1, "rally_id": "…", "game": 1, "start_ms": 1200, "end_ms": 9800}],
 "next_cursor": null}
```

- `items` are the rallies behind that metric and side (the snapshot's `rallies`), ordered by `start_ms` (the video order; `number` is the sheet's match-wide rally number, api-sprint-02 §2.1). `total` is n, the number behind the metric ("see all n"). Numbers and ids come from one sheet version (`sheet_version`).
- `limit`: 1-10, default 10 (FR-103 "up to 10"). "See all" pages through with `cursor`; each page holds at most 10 items.
- Each item opens its video moment with the Sprint 2 route `GET /matches/{match_id}/rallies/{rally_id}/media` (presigned GET, TTL ≤ 15 min, `start_ms` of the rally; api-sprint-02 §3, NFR-055). The evidence response itself carries no media URL.
- Refusals: 401; 404 (§1.1); **404** for a `metric_id` that is not a published entry (unknown, draft or deprecated look the same, FR-102); 422 `validation_failed` with `side`/`side_invalid` (missing or not `A`/`B`), `limit`/`invalid` (not an integer 1-10), `cursor`/`invalid`.

## 4. Deletion (ST-050, ST-051; FR-006, FR-007; NFR-066)

### 4.1 `DELETE /matches/{match_id}`

- **Body (required):** `{"confirm": "delete"}`, exactly this object. The client sends it only after the confirmation page that states the consequences (FR-006, DES FR-UX-90: "Deletes the video, clips, tags and stats for this match …", "cannot be undone"); the server check stops a stray or replayed request from deleting without that step (judgment). `Content-Type: application/json`.
- **Success: 202 Accepted**, `Cache-Control: no-store`:
  `{"deleted": true, "purge_due_by": "2026-10-14T09:15:00Z"}` — hidden from this response on; every object and row purged by `purge_due_by` (deleted_at + 7 days, ADR 0006). 202 because the purge is still to come (NFR-066 b).
- **Refusals,** checked in this order: 401; 403 Origin; **404** (§1.1, also for a match already deleted, so a second DELETE answers 404 and changes nothing); **422 `validation_failed`** with `{"field": "confirm", "code": "confirmation_required"}` when the body is missing, empty, not an object, or `confirm` is not `"delete"`, and `{"field": null, "code": "unknown_field"}` for any other key. Nothing is written on any refusal (IT-03-06).
- RFC 9110 gives a DELETE body no generic meaning; this API defines it, and every hop of the stack (Caddy, the Next.js `/api` rewrite, FastAPI) passes it (ADR 0019 rewrite limits apply). A client that cannot send a body cannot delete; there is no query-string alternative (judgment: one way only).

### 4.2 `DELETE /me`

- **Body (required):** `{"confirm": "delete"}` (same rule; the account page states that all matches, videos, tags and stats go, the account is signed out on every device, and it cannot be undone).
- **Success: 202 Accepted**, `{"deleted": true, "purge_due_by": "…"}`, with the `POST /auth/sign-out` headers: the session cookie cleared (`Max-Age=0`, same attributes) and `Clear-Site-Data: "cache"`. Every session of the account is gone in the same transaction (FR-007): any old cookie now gets 401.
- Signing in again with the same address (magic link) creates a **new, empty account** with a new id (deletion-and-purge.md §3.2; PM-1 may change this default).
- **Refusals:** 401 (also for a second DELETE, since the session is gone); 403 Origin; 422 as in §4.1. Nothing is written on a refusal (IT-03-08).

### 4.3 After deletion (observable)

| Request | After `DELETE /matches/{id}` | After `DELETE /me` |
|---|---|---|
| `GET /matches` (owner) | the match is not listed | 401 |
| any route naming the match (match, media, video, uploads `HEAD`/`PATCH`, score sheet, commands, stats, evidence, label routes) | 404 | 401 |
| a rally media URL issued before the delete | works until its TTL ends or the purge deletes the object, whichever is first (≤ 15 min, NFR-055); 404 from the store once purged (G03-03 b) | same |
| purge pass (`python -m racket.platform.purge --once`) | no row in any table with a `match_id`, `owner_id` or `account_id` column, and no stored object, for that match | same for every match of the account, and the account row |

### 4.4 Purge job contract (for the harness and the scorecard)

- Command: **`python -m racket.platform.purge --once`**, exit 0 (every due item done), 1 (an item failed; retried next pass), 2 (usage or configuration). Unchanged from `statscontract.PURGE_ONCE`.
- Where: the **`purge`** Compose service (ADR 0038, Accepted). On demand: `$DC exec -T purge python -m racket.platform.purge --once`. Not the `worker` service (ST-042).
- Schedule: `PURGE_INTERVAL_S`, default 86400, refused above 86400 (NFR-066 c); G03-03 (c) greps it in `$DC config`.
- Test seam: `racket.platform.purge:main(argv) -> int` (as `tests/support/stats.py` `PURGE_MAIN` assumes).
- Abandoned uploads (ST-038) are expired by the same pass: owner `HEAD`/`PATCH` → **410 `upload_expired`** (api-sprint-01 §6.4), others 404.

## 5. Full Tag labelling (ST-052; FR-150, FR-151)

### 5.1 Access

- The tool exists only for accounts with the **labeller role**. For any other account every label route answers **404 `not_found`**, the same as a missing match (FR-150 "not available"; IT-03-11).
- In Sprint 3 a labeller labels **matches their own account owns** (the team uploads its consented footage under the labeller account). Labelling another account's match needs the player's training consent (FR-009, Sprint 4) and is not offered; such a match is 404 (§1.1).
- A labeller's own match **without a consent record** is refused with **409 `no_consent`**, message "This match has no consent record for labelling." (the labeller is told why, IT-03-11). A match without a probed video (no fps or duration) is **409 `match_not_ready`**.
- Order of checks: session (401) → Origin on POST (403) → labeller role (404) → owner filter (404) → consent (409 `no_consent`) → video facts (409 `match_not_ready`) → body (422).

### 5.2 Routes

| Route | Body | Success | Refusals (besides §5.1) |
|---|---|---|---|
| `GET /label/matches/{match_id}` | none | 200 `{"match_id", "fps", "frame_count", "players": ["A1","A2","B1","B2"], "version", "document"}` — `document` is the current `full-tag-labels/v1` document (§5.3) | — |
| `POST /label/matches/{match_id}/events` | one label object: `{"type": "rally", "start_frame", "end_frame", "outcome"}`, `{"type": "hit", "frame", "hitter", "facets"?}` or `{"type": "bounce", "frame", "visible", "court_xy_m"}` (gold-label-schema §4) | **201** `{"version", "rallies": <count>, "events": <count>}` | 422 `invalid_label` (§5.4); 429 `rate_limited` (the scorebook per-account rate, api-sprint-02 §3 Limits) |
| `GET /label/matches/{match_id}/export` | none | 200 the `full-tag-labels/v1` document, `Content-Disposition: attachment; filename="labels-<match_id>.json"` | — |

- The video for frame stepping is the Sprint 2 `GET /matches/{match_id}/video` link (owner route; the labeller owns the match).
- `fps` and `frame_count` come from the probed media facts: `frame_count = floor(duration_ms × fps / 1000)` (60 s at 60 fps → 3,600). A variable-frame-rate video is `match_not_ready` in Sprint 3 (frame numbers would not be stable; DOM/CV-01, judgment).
- `players` are the match's slots (doubles `A1 A2 B1 B2`, singles `A1 B1`), never nicknames.
- Concurrency: commands on one match are serialised under the label session's row lock; `version` goes up by one per accepted command. There is no edit or delete of a label in Sprint 3 (not in FR-150's acceptance; a later story).

### 5.3 The export document

Exactly `full-tag-labels/v1` (`docs/data/gold-label-schema.md` §4), built by `FullTagSession.export()`, so it always validates (`racket.dataset.labels.validate_labels(doc) == ()`, IT-03-11). `clip` is `"match:<match_id>"` (never an object key). The document holds frames, slots and outcome values only; the consent reference is never in it.

### 5.4 `invalid_label` (422)

`{"error": {"code": "invalid_label", "message": "This label is not valid.", "fields": [{"field": "frame", "code": "invalid"}, …]}}` — one entry per problem the domain lists, with `field` the label key (`type`, `frame`, `hitter`, `facets`, `start_frame`, `end_frame`, `outcome`, `visible`, `court_xy_m`, or `null` for the whole object) and `code` ∈ `invalid`, `unknown_field`, `outside_clip`, `no_rally`, `overlaps_rally`, `out_of_order`, `not_a_player`. The message is fixed; label values are never echoed or logged (NFR-057, IT-03-13). Nothing is stored (IT-03-11).

### 5.5 Labeller administration (CLI, not HTTP)

`python -m racket.dataset.admin` (seam `racket.dataset.admin:main(argv) -> int`, as `tests/support/stats.py` `LABELLER_ADMIN` assumes), run by an operator in the `api` container (app identity):

- `grant-labeller --account <account_id>` / `revoke-labeller --account <account_id>`: the role lives in Identity & Players (`players.public.has_role(session, account_id, "labeller")`); Dataset reads it only through that port.
- `consent --match <match_id> --record <reference>`: writes the team-held consent record (`ConsentRecord.create`: a reference code of 1-64 `A-Z a-z 0-9 . _ : -`, never a name or address; `recorded_by` is the operator's pseudonymous account id given with `--by`).
- Exit 0 done, 1 refused (unknown account or match, invalid reference), 2 usage. Logs ids only.

## 6. Codes added in Sprint 3

### 6.1 Error codes (`error.code`)

| Code | Status | Message (fixed) | Routes |
|---|---|---|---|
| `no_consent` | 409 | "This match has no consent record for labelling." | label routes |
| `invalid_label` | 422 | "This label is not valid." | `POST /label/matches/{id}/events` |
| `not_found` | 404 | (unchanged) | also: deleted match, unpublished metric id, label routes for a non-labeller |
| `validation_failed` | 422 | (unchanged) | evidence query; delete confirmation |
| `match_not_ready` | 409 | (unchanged, api-sprint-02) | label routes without probed video facts |

### 6.2 Field codes (`error.fields[].code`, closed)

| Field | Codes |
|---|---|
| `side` (evidence) | `side_invalid` |
| `limit`, `cursor` (evidence) | `invalid` |
| `confirm` (delete) | `confirmation_required` |
| `null` | `unknown_field`, `invalid` |
| label keys (§5.4) | `invalid`, `unknown_field`, `outside_clip`, `no_rally`, `overlaps_rally`, `out_of_order`, `not_a_player` |

## 7. Status per route (BOLA matrix additions, IT-03-05; NFR-051)

| Route | No session | Other account | Deleted / missing | Owner |
|---|---|---|---|---|
| `GET /matches/{id}/stats` | 401 | 404 | 404 | 200 |
| `GET /matches/{id}/stats/{metric_id}/evidence` | 401 | 404 | 404 | 200 / 404 (unpublished metric) / 422 |
| `DELETE /matches/{id}` | 401 | 404 | 404 | 202 / 422 |
| `GET /label/matches/{id}` | 401 | 404 | 404 | 404 (not a labeller) / 200 / 409 |
| `POST /label/matches/{id}/events` | 401 | 404 | 404 | 404 (not a labeller) / 201 / 409 / 422 |
| `GET /label/matches/{id}/export` | 401 | 404 | 404 | 404 (not a labeller) / 200 / 409 |

`DELETE /me` takes no id (not in the matrix; IT-03-08 covers it). The inventory test must see all six routes above; QA moves each probe from `MATCH_ID_ROUTES_03` into `MATRIX` when its route lands (TCR row 2026-10-07).

## 8. Configuration

| Variable | Default | Rule |
|---|---|---|
| `PURGE_INTERVAL_S` | 86400 | integer 1..86400 (ADR 0038) |
| `PURGE_BATCH` | 100 | integer ≥ 1; matches per pass before the pass ends (the next pass continues) |
| `PURGE_MIN_AGE_S` | 0 | integer ≥ 0; a tombstone is due this long after deletion |
| `PURGE_ALERT_AFTER_S` | 518400 | integer ≥ 1; `purge.overdue` at ERROR past this age (6 days) |

No low-sample threshold is configurable by environment (ADR 0041); they live in the versioned metric dictionary.

## 9. Not decided here (owners)

| Item | Owner |
|---|---|
| PM-1: what signing in again after account deletion gives (default: a new, empty account) | product-manager |
| SEC-1 threat notes for every route above (deletion ordering, revocation, labeller privilege, consent) | security-privacy-engineer |
| The screens (stats D, evidence E, deletion X, Full Tag L) and their copy | principal-designer (PD-1, DR-03) |
| Edit/delete of a label; labelling another account's match (FR-009) | product-manager, Sprint 4 |
| Data export (FR-010) | Sprint 4+ |
