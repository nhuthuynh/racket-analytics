# API contract: Sprint 4 (plan, done and swap, age, retention, consent, quotas)

- **Status:** Accepted for build (principal-engineer, 2026-10-17, gate ticket PE-4). Written before the routes exist. The route and field names the plan and scorecard assumed (`docs/sprints/04/goal-scorecard.md`) are kept, so no scorecard method changes. A change after merge goes through the story's ticket PR with a row in its decisions file, and changes the QA harness (`scripts/measure/live_plan.py`, `live_privacy.py`) in the same PR (ADR 0033 rule 2).
- **Domain design:** [`coaching-plan.md`](coaching-plan.md). **Security:** SEC-4 threat notes (`docs/security/threat-notes-sprint-04.md`) are acceptance criteria of the stories; §8 here is the BOLA list SEC-4 checks.
- **Builds on:** `api-sprint-00.md` .. `api-sprint-03.md`, all still in force: `/api` base path, `application/json`, UUIDv4 ids (malformed → 404), closed request schemas (unknown key → 422 `{"field": null, "code": "unknown_field"}`), the error envelope with `fields` on 422 and `retry_at` on 429 (api-sprint-01 §1.1), fixed messages that never echo input, `Cache-Control: no-store`, the Origin check on state-changing requests, the session cookie.

## 1. Conventions added

1. **Owned resources.** `/me/plan` names no id: it is the session account's plan. A session or assignment id that is not in the caller's current plan (another account's, an old plan's, unknown, malformed) is **404 `not_found`**, same body.
2. **Flags.** A route behind a flag (§4-§7) answers **404 `not_found`** while its flag is off, and no response carries a field it adds; behaviour is as in Sprint 3 (G04-09 a, G04-10 c). Flags: `FEATURE_AGE_GATE`, `FEATURE_RETENTION_SETTING`, `FEATURE_TRAINING_CONSENT`, `FEATURE_QUOTAS`, all default off (ADR 0051 rule 4).
3. **`GET /config/public`** (ST-067; no session; 200, `Cache-Control: no-store`): `{"features": {"age_gate": false, "retention_setting": false, "training_consent": false, "quotas": false}, "coaching": {"weakness_unit": "rallies_lost_per_game"}}`. Nothing else (no limits, no secrets).

## 2. Plan (ST-061b; FR-120..FR-123; NFR-019)

### 2.1 `POST /me/plan`: generate (or replace) the current plan

Body (closed):

| Field | Required | Rule (field code on failure) |
|---|---|---|
| `minutes_per_session` | yes | integer 15-180 (`out_of_range`); 15 because a session must hold a 5-minute warm-up under the 40% cap (coaching-plan QD-PL-03: ⌊0.4 × 15⌋ = 6) |
| `sessions_per_week` | yes | integer 1-7 (`out_of_range`) |
| `weekly_minutes` | no (default `minutes_per_session × sessions_per_week`) | integer ≥ `sessions_per_week × 15` (`out_of_range`), so the per-session budget ⌊`weekly_minutes` / `sessions_per_week`⌋ is ≥ 15 too |
| `players_available` | yes | integer 1-4 (`out_of_range`) |
| `equipment` | yes (may be `[]`) | unique items from `wall`, `half_court`, `full_court`, `ball_machine`, `partner_feeder` (`unknown_value`, `duplicate`) |
| `level` | yes | `beginner` \| `intermediate` \| `advanced` (`unknown_value`) |

A missing required field is `required`; a wrong JSON type is `invalid`. Checks in order: 401 → 403 Origin → 422 → ranking → assembly → save. **201** with the plan (§2.3) and `Location: /me/plan`. An existing plan is replaced in the same transaction (its done marks and reasons go with it).

Refusals: **409 `no_tagged_match`** "Tag at least one match to get a plan." (no match in scope, coaching-plan §3); **409 `no_plan_fits`** "No plan fits these settings. Try more time or equipment." (assembly infeasible); **409 `plan_conflict`** (§3.4). Nothing is written on a refusal. Latency: request → 201 p95 ≤ 5 s (NFR-019), measured in IT-04-02 and G04-02 (a).

### 2.2 `GET /me/plan`

200 with the plan; **404 `no_plan`** "You have no plan yet." when there is none. A stale plan is regenerated first (coaching-plan §8): 200 with `"regenerated": "source_match_deleted"`, or 404 `no_plan` when no tagged match remains. Read p95 ≤ 300 ms, p99 ≤ 800 ms at 50 RPS (G04-02 c).

### 2.3 Plan representation

```json
{"id": "…", "version": 3, "created_at": "2026-10-17T09:00:00Z", "content_digest": "sha256:…",
 "library_version": "…", "regenerated": null,
 "unofficial": true, "label": "unofficial scoring (rules not yet verified)",
 "drills_verified": false,
 "preferences": {"minutes_per_session": 30, "sessions_per_week": 3, "weekly_minutes": 90,
                 "players_available": 1, "equipment": ["wall"], "level": "intermediate"},
 "ranking": {"unit": "rallies_lost_per_game", "side_out_verified": false, "games": 1, "rallies": 14,
             "skipped_matches": 0,
             "weaknesses": [{"id": "unforced_errors", "name": "Unforced errors", "metric_id": "AN-04",
                             "rank": 1, "per_game": 2.0, "on_serve_per_game": 1.0,
                             "on_receive_per_game": 1.0, "conceded_per_game": 1.0}]},
 "limited_data": {"rallies": 14},
 "unfitted": [{"weakness_id": "…", "reason": "no_drill_fits"}],
 "sessions": [{"id": "…", "week": 1, "index": 1, "minutes_budget": 30, "done": false, "done_at": null,
               "assignments": [{"id": "…", "position": 1, "drill": {"id": "pb.warm-up.…", "version": 1,
                                "name": "…", "players": 1, "needs": ["wall"], "skills": ["warm-up"]},
                                "minutes": 8, "weakness_id": null, "warm_up": true,
                                "citation": {"metric_id": "AN-01", "metric_version": "0.1", "side": "A",
                                             "value": 0.5714, "n": 7, "k": 4, "low_sample": true,
                                             "rally_ids": ["…"],
                                             "evidence": [{"match_id": "…", "n": 7}]},
                                "why": "Rallies won on serve: 57% of 7 serves"}]}]}
```

- `unofficial`/`label` as stats (api-sprint-03 §2.1); `drills_verified` is `false` while any drill in the plan is not `verified` (interim notice, P15). `limited_data` is `null` unless QD-PL-06 holds. Weakness `name` and `why` texts come from the catalogue and the metric dictionary; the FE may render its own copy from the ids (PD-4).
- `citation.side` is the player's side in the cited matches (a list in `evidence` when sides differ across matches; `side` is then the side of the first). `rally_ids`: at most 10, video order per match, matches in `evidence` order; `evidence[].n` is the per-match n, so "Show me" / "see all n" call `GET /matches/{match_id}/stats/{metric_id}/evidence?side=…` per match (api-sprint-03 §3).
- Numbers: proportions rounded to 4 places, per-game values to 2.

## 3. Follow-through (ST-062; FR-124)

### 3.1 `POST /me/plan/sessions/{session_id}/done`

- Header **`Idempotency-Key`** (required): the client's op id, 1-64 characters `A-Z a-z 0-9 - _` (a UUID in the web client). Missing or malformed → 422 with `{"field": "Idempotency-Key", "code": "required" | "invalid"}`. No body (an empty object is accepted).
- **200** `{"session_id": "…", "done": true, "done_at": "…", "plan_version": 4, "replayed": false}`.
- Same key again (offline replay) → the stored result, `"replayed": true`, version unchanged. A new key on a session already done → 200, version unchanged (no-op). The same key for a different session → **409 `idempotency_key_reused`**. A session of a replaced plan → 404 (the client drops the op and reloads the plan).

### 3.2 `DELETE /me/plan/sessions/{session_id}/done` (undo)

200 `{"session_id", "done": false, "done_at": null, "plan_version"}`; on a session not done: 200, version unchanged.

### 3.3 `POST /me/plan/assignments/{assignment_id}/swap` ("Not for me")

- Body (closed): `{"reason": "…"}` optional, 1-200 characters after trim (`too_long`, `invalid`). Stored with the plan, deleted with it, never logged or echoed in errors.
- **200** with the whole updated session (§2.3 session object) and `plan_version`; the assignment keeps its `id`, its `drill`, `minutes`, `citation` and `why` change; the metric is the same.
- **409 `no_alternative`** "No other drill fits your settings for this." — plan unchanged, version unchanged. **409 `session_done`** "This session is already done." Refused before any write.

### 3.4 Concurrency

Commands on one plan are serialised by the plan's version check (coaching-plan §5); after one internal retry a lost race is **409 `plan_conflict`** "Your plan changed. Reload it.". `plan_version` in every follow-through response lets the client detect a change.

## 4. Age confirmation (ST-068a; FR-003; flag `FEATURE_AGE_GATE`)

- With the flag on, `POST /auth/exchange` for an address with **no account** sets the session cookie on a **pending sign-in** (no account row; `pending_sign_ins`, 0019). Every route except `POST /me/age-confirmation`, `POST /auth/sign-out`, `GET /config/public` and the auth routes answers **403 `age_confirmation_required`** "Please confirm your age to continue." for a pending sign-in, and for an existing account whose `age_confirmed_at` is null.
- `POST /me/age-confirmation` body `{"is_adult": true | false, "confirm": "delete"}` (closed; `is_adult` required, `required`/`invalid`; `confirm` optional, see below):
  - `true` → **200** `GET /me` body plus `"age_confirmed_at"`. A pending sign-in becomes an account (new id) in the same transaction; only the timestamp is stored, never a birth date.
  - `false` → **403 `under_age`** (interim text, PM-4 register, pending legal review), the pending sign-in deleted and the cookie cleared (`Max-Age=0`); **0 account rows** are created. For an existing unconfirmed account (which may hold matches, videos, tags and stats), `false` deletes it as `DELETE /me` does **only with the same guard**: the body must also carry `"confirm": "delete"`, sent by the client only after the account-deletion page of api-sprint-03 §4.2 ("cannot be undone"). Without it the answer is **422 `validation_failed`** `{"field": "confirm", "code": "confirmation_required"}` and nothing changes (the account stays unconfirmed and gated). A pending sign-in holds no data, so `confirm` is not needed there and is ignored. (Judgment, SEC-4 to confirm.)
- Flag off: no pending state; exchange creates accounts as in Sprint 1; the route is 404.

## 5. Video retention (ST-069; FR-008; ADR 0006; flag `FEATURE_RETENTION_SETTING`)

- `GET /me/retention` → 200 `{"review_video_days": 90, "choices": [30, 90, 365, null]}` (`null` = until I delete).
- `PUT /me/retention` body `{"review_video_days": 30 | 90 | 365 | null}` (closed; `unknown_value`, `required`) → 200 same shape. Applies to every match of the account from the next purge pass.
- The match representation gains `review_video_delete_at`: analysed time (R1: the probe's success time) + the account's days, or `null` (until I delete, or no video yet).
- The purge deletes review video objects whose date passed (objects first, then the media row; tags, stats and plans stay). Dev/test-only option `python -m racket.platform.purge --once --now-offset-days N` (refused with exit 2 when `APP_ENV` is `staging` or `prod`), as the scorecard's G04-09 method calls it.

## 6. Training-data consent (ST-070; FR-009; flag `FEATURE_TRAINING_CONSENT`)

- `GET /me/training-consent` → 200 `{"opt_in": false, "changed_at": null}`. `PUT /me/training-consent` body `{"opt_in": bool}` (closed) → 200 same shape; each change writes one `training_consent_events` row; a PUT with the current value writes nothing.
- Label-set and gold-manifest builds read `racket.players.public` consent at build time: only opted-in owners' matches; revoke → excluded from the next build; frozen gold-set versions are not edited (OQ-06, ADR 0023).

## 7. Rate limit and storage quota (ST-072a; FR-160; NFR-023; flag `FEATURE_QUOTAS`)

| Key | Limit (setting) | Route |
|---|---|---|
| `match:create:<account_id>` | `MATCH_CREATIONS_PER_HOUR` = 10 per 3600 s | `POST /matches` |
| `match:create:ip:<client ip>` | 60 per 3600 s (judgment; SEC-4 confirms) | `POST /matches` |

- Counted only after the body validates (a 422 spends no slot). Over the limit: **429 `rate_limited`** with `retry_at` (RFC 3339 UTC) and `Retry-After`, nothing written (api-sprint-01 §1.1; `racket.platform.ratelimit`).
- **Storage quota** (`STORAGE_QUOTA_BYTES`, 20 GB, (judgment) until P8): at `POST /matches/{id}/uploads`, a new check **4a** between api-sprint-01 §6.3 checks 4 and 5: used = bytes of the account's live stored videos + declared `Upload-Length` of its open receiving sessions; if used + this `Upload-Length` > limit → **429 `storage_quota_exceeded`** "You have used your storage.", `retry_at: null`, and the extra key `"quota": {"used_bytes", "limit_bytes", "requested_bytes"}`. Refused before any byte is stored; `rejection` is not set; no rate slot spent. A resumed upload (`PATCH`) is never counted again.
- The `quota` key changes the error-body key set pinned by the regression suite: QA owns that test change (TCR row in ST-072a).
- `GET /me/quota` → 200 `{"storage": {"used_bytes", "limit_bytes"}, "match_creations": {"limit": 10, "window_s": 3600, "used": 3, "next_slot_at": null}}` for Q-01.

## 8. Status per route (BOLA matrix additions, IT-04-03; NFR-051)

| Route | No session | Other account's id | Unknown / malformed id | Owner | Flag off |
|---|---|---|---|---|---|
| `POST /me/plan` | 401 | n/a (no id) | n/a | 201 / 409 / 422 | always on |
| `GET /me/plan` | 401 | n/a | n/a | 200 / 404 `no_plan` | always on |
| `POST /me/plan/sessions/{session_id}/done` | 401 | 404 | 404 | 200 / 409 / 422 | always on |
| `DELETE /me/plan/sessions/{session_id}/done` | 401 | 404 | 404 | 200 | always on |
| `POST /me/plan/assignments/{assignment_id}/swap` | 401 | 404 | 404 | 200 / 409 / 422 | always on |
| `POST /me/age-confirmation`, `GET/PUT /me/retention`, `GET/PUT /me/training-consent`, `GET /me/quota` | 401 | n/a | n/a | 200 / 403 / 422 | 404 |

Only the three id routes join `MATRIX` in `backend/tests/regression/bola.py` (kind `plan_session`, `plan_assignment`), additions only; the `/me/*` routes take no id and are covered by their ITs (IT-04-02, IT-04-06..09).

## 9. Codes added

| Code | Status | Message (fixed) | Routes |
|---|---|---|---|
| `no_plan` | 404 | "You have no plan yet." | `GET /me/plan` |
| `no_tagged_match` | 409 | "Tag at least one match to get a plan." | `POST /me/plan` |
| `no_plan_fits` | 409 | "No plan fits these settings. Try more time or equipment." | `POST /me/plan` |
| `plan_conflict` | 409 | "Your plan changed. Reload it." | plan commands |
| `no_alternative` | 409 | "No other drill fits your settings for this." | swap |
| `session_done` | 409 | "This session is already done." | swap |
| `idempotency_key_reused` | 409 | "This request id was already used." | done |
| `age_confirmation_required` | 403 | "Please confirm your age to continue." | every route but §4's list |
| `under_age` | 403 | interim text (PM-4 register) | `POST /me/age-confirmation` |
| `storage_quota_exceeded` | 429 | "You have used your storage." (`retry_at: null`, `quota`) | upload creation |
| `rate_limited` | 429 | (unchanged) | also `POST /matches` |

Field codes added: `out_of_range`, `unknown_value`, `duplicate`, `too_long` (besides the existing `required`, `invalid`, `unknown_field`). User-facing copy is PD-4's and PM-4's; messages here are server defaults.

## 10. Flag-on E2E strategy

- **Default per-PR stack:** every flag off; the existing and E2E-04-01..05 specs run unchanged in `web-checks`.
- **Flag-on behaviour per PR:** integration tests build the app with `Settings(feature_…=True)` (IT-04-06..09) and Vitest renders with a mocked `GET /config/public`; each flag has an on and an off test.
- **Flag-on E2E:** a Playwright project **`flags-on`** (`web/playwright.config.ts`, selected by `PW_PROJECTS=flags-on`) runs `web/e2e/sprint-04/flags-on/*.spec.ts` (E2E-04-06 age, E2E-04-07 privacy settings, E2E-04-08 over-limit) against a stack started with `FEATURE_AGE_GATE=1 FEATURE_RETENTION_SETTING=1 FEATURE_TRAINING_CONSENT=1 FEATURE_QUOTAS=1`; nightly and by the verifier (G04-07), not per PR (judgment: flags on would change every per-PR journey).

## 11. Configuration (ST-067 adds to `infra/env.example`)

`COACHING_WEAKNESS_UNIT=rallies_lost_per_game` (any other value refuses to start); `FEATURE_AGE_GATE`, `FEATURE_RETENTION_SETTING`, `FEATURE_TRAINING_CONSENT`, `FEATURE_QUOTAS` (default `false`); `AGE_MINIMUM=18`; `RETENTION_CHOICES_DAYS=30,90,365,none`; `RETENTION_DEFAULT_DAYS=90`; `MATCH_CREATIONS_PER_HOUR=10`; `STORAGE_QUOTA_BYTES=21474836480`. Sources: ADR 0023 OQ-05/07/13, ADR 0051 rule 4; storage quota (judgment), P8.
