# Threat notes, Sprint 4: plan routes, R1 privacy (age, retention, consent), quotas and billing alerts

- **Status:** v4 delta to [`threat-model-v0.md`](threat-model-v0.md) and the Sprint 1-3 deltas ([`threat-model-sprint-03.md`](threat-model-sprint-03.md) is the latest). All still hold. Gate ticket **SEC-4** (sprint-04 §3.7; ADR 0047 rule 2). Precondition for ST-061a/b, ST-062, ST-068a, ST-069, ST-070, ST-072a and ST-073.
- **Date:** 2026-10-17. **Author:** security-privacy-engineer.
- **Method:** STRIDE per element plus abuse cases (judgment), as in v0. ASVS 5.0 numbers from [`asvs-l2-checklist.md`](asvs-l2-checklist.md).
- **Reviewed:** `docs/architecture/api-sprint-04.md` and `coaching-plan.md` (PE-4 branch `s04/pe-4-…`, not yet on `main`, so not linked); [`deletion-and-purge.md`](../architecture/deletion-and-purge.md); ADR [0006](../decisions/0006-retention-and-deletion-defaults.md), [0023](../decisions/0023-product-owner-decisions-2026-10-05.md), [0042](../decisions/0042-deletion-tombstones-now-purge-objects-before-rows.md), [0045](../decisions/0045-purge-keys-fail-closed-owned-writes-lock-the-account-snapshots-lock-the-match.md), [0051](../decisions/0051-sprint-4-lands-a-runnable-prototype-first-privacy-and-quotas-behind-default-off-flags.md); `backend/src/racket/platform/ratelimit.py`; `players/domain.py` (`client_ip`); `video_ingest/api.py`, `service.py`; `backend/tests/regression/bola.py`.
- **Rule (ADR 0022 rule 4):** every control that names a story is an **acceptance criterion of that story** and needs a red test first. Status: **D** designed, story not started (the named test is the red test to write first); **O** open, a finding in §9 must be resolved in the story; **C** in place with its test.
- **Actors:** A1 Ivy, the owner; A2 Carlos, another signed-in user; A3 an anonymous client; A16 (new) a self-declared under-18 person; A17 (new) a client that replays or forges offline ops; A10 a component or operator with database access.

## 1. New assets

| Asset | Class | Where | Retention |
|---|---|---|---|
| Training plan (preferences, sessions, assignments, citations with `rally_ids`, done marks, swap reasons) | Personal (performance data of the account holder) | `coaching` tables (0018) | Replaced by the next `POST /me/plan`; deleted with the account (coaching-plan §8) |
| Idempotency records of done ops | Personal (ids, times) | 0018 | Deleted with the plan (judgment) |
| Pending sign-in (address, session) | Personal (contact) | `pending_sign_ins` (0019) | Until confirmed, refused or expired (§3, T4-AG-3) |
| `age_confirmed_at` | Personal | `accounts` (0019) | With the account. **No birth date, no age, no "refused" record** |
| Retention choice | Personal (setting) | 0020 | With the account |
| Consent state and `training_consent_events` | Personal (audit) | 0021 | With the account; events kept as the audit trail until account purge (judgment) |
| Rate-limit rows `match:create:*`, quota usage | Pseudonymous (ids, IP) | `rate_limit_events` | Window length; pruned by the purge pass (SEC-S3-TM-04) |
| Billing alert rules and their notification target | Config; the target may be a secret | `infra/` (ST-073) | In git: rules only, no target secret (§7) |

## 2. Plan routes: BOLA, replayed done ops, swap abuse (ST-061b, ST-062; FR-120..FR-124; NFR-051)

| ID | STRIDE | Threat | Control (acceptance criterion) | ASVS / source | Story | Test | Status |
|---|---|---|---|---|---|---|---|
| T4-PL-1 | I/T | Carlos marks Ivy's session done, undoes it or swaps her assignment by guessing or copying a `session_id` / `assignment_id` | Lookup by id **joined to the caller's current plan** (`plan.account_id = session account`), in the repository, never "load by id then compare". Other account's, an old plan's, unknown and malformed ids all → the same 404 `not_found` body. Nothing written | 8.2.2, 8.3.1 [AQS/SEC-09, SEC-03]; NFR-051 | ST-061b, ST-062 | IT-04-03 (BOLA MATRIX rows §8); IT: Ivy's own id from a replaced plan → 404 | D |
| T4-PL-2 | I | **The plan cites another account's data.** The ACL read of `analytics.public` (rally outcomes, metric values, evidence rally ids) is not filtered by owner, so Ivy's plan shows Carlos's `match_id`/`rally_ids` | The Coaching ACL takes the account id as a required argument and reads only matches owned and not tombstoned (`owns_match` filter); evidence ids are copied from the owned read model, never from the request | 8.2.2; NFR-051 | ST-061b (ST-057 ACL) | IT: Ivy and Carlos both have tagged matches → every `citation.evidence[].match_id` and `rally_ids` in Ivy's plan belong to Ivy's matches | D |
| T4-PL-3 | S/I | **Cross-account idempotency oracle.** Op ids are stored in one global namespace: Carlos replays Ivy's `Idempotency-Key` (seen in a shared device log or guessed) and gets her stored result (`session_id`, `done_at`), or a 409 `idempotency_key_reused` that tells him the key exists | Idempotency records keyed by **`(account_id, key)`**, unique per account. Order: 401 → Origin 403 → 422 header shape → **ownership 404** → idempotency lookup. Another account's key is just a new key for Carlos | 8.2.2; 2.x business logic (judgment) | ST-062 | IT: Carlos sends Ivy's key on Ivy's session → 404; on his own session → 200 `replayed: false`; unit: the record key includes the account | **O (SEC-S4-TM-02)** |
| T4-PL-4 | T | A replayed or reordered offline op corrupts the plan: a done replayed after undo re-marks it, or an op for a replaced plan writes to the new one | Replay with the same key returns the stored result and **writes nothing** (version unchanged); ops target a session id, and ids of a replaced plan → 404 (client drops the op). Undo then a replay of the earlier done: the stored result is returned, the session stays undone (judgment: last explicit command wins; the replay is not a new command) | 2.x business logic; FR-124 | ST-062 | IT: done(k1) → undo → done(k1) again → `replayed: true`, `done: false` in a fresh `GET /me/plan`; done(k1) after `POST /me/plan` replaced the plan → 404 | D |
| T4-PL-5 | D | Unbounded idempotency records: a client sends a new key on every retry (or a script loops), growing the table | New key on an already-done session is a no-op **and stores no record** (contract §3.1); one record per session at most; records deleted with the plan | 2.4.1 [AQS/SEC-10] | ST-062 | Unit: second key on a done session writes no row | D |
| T4-PL-6 | D | **Swap and generate abuse.** `POST /me/plan` costs up to p95 5 s of CPU (NFR-019) and swap re-runs assembly; a loop of either starves the API worker pool | Per-account limit `plan:generate:<account_id>` 30 per hour and `plan:swap:<account_id>` 120 per hour (judgment) on the existing `RateLimiter`, counted after validation, 429 `rate_limited` with `retry_at`; behind no flag (the plan is always on) | 2.4.1 [AQS/SEC-10]; NFR-023 | ST-061b, ST-062 | IT: the 31st generate in an hour → 429, nothing written | **O (SEC-S4-TM-01)** |
| T4-PL-7 | I/T | Swap `reason` free text is stored XSS, a log-injection vector, or leaks in errors | Closed body, 1-200 chars after trim, stored as data; never logged, never echoed in an error (contract §3.3); rendered as text by React (no `dangerouslySetInnerHTML`) | 1.2.x output encoding; 16.2.5 [AQS/SEC-04] | ST-062, ST-063c | IT: a reason with `<script>` and `\n` → 200, absent from captured logs; L11 fuzz on `reason` | D |
| T4-PL-8 | E | Mass assignment: `account_id`, `version`, `done`, `drill` in plan bodies | Closed bodies; unknown key → 422 `unknown_field`; the client cannot choose a drill id on swap | 8.2.3; NFR-052 | ST-061b, ST-062 | IT-04-02 / L11 (`unknown_field`) | D |
| T4-PL-9 | I | A plan keeps citations (`rally_ids`, `match_id`) of a deleted match past the deletion window, because it is only regenerated when read | The purge pass, after it purges a match (objects then rows, ADR 0042), marks plans citing it stale **and deletes their citation rows**, so nothing of the match survives the ≤ 7-day window even if the plan is never read again | 14.2.7 [AQS/SEC-05]; NFR-066 (b) | ST-061a/b (with the purge) | IT: delete a cited match → one purge pass → 0 citation rows with its id; `GET /me/plan` → regenerated or 404 `no_plan` | **O (SEC-S4-TM-03)** |

## 3. FR-003 age confirmation: no account row for under-18 (ST-068a; flag `FEATURE_AGE_GATE`)

| ID | STRIDE | Threat | Control (acceptance criterion) | ASVS / source | Story | Test | Status |
|---|---|---|---|---|---|---|---|
| T4-AG-1 | I | **Data of a self-declared minor is kept.** An account row, a birth date, an age, or a "refused" marker on the address is stored | Pending sign-in only (no `accounts` row) until `is_adult: true`. `false` → pending row deleted in the same transaction, cookie cleared (`Max-Age=0`), server session deleted, **0 account rows, no deny-list of the address**. Only `age_confirmed_at` (a timestamp) is stored on success; no birth date column exists in 0019 | 14.2.x [AQS/SEC-05]; FR-003; OQ-05 (ADR 0023) | ST-068a | IT-04-06: count `accounts` before/after a `false` → equal; schema test: no column named like `birth`/`dob`/`age` except `age_confirmed_at` | D |
| T4-AG-2 | E | A pending sign-in (or an unconfirmed existing account) reaches data routes | **Deny by default** in one dependency, not per route: every route except the four allowed (`POST /me/age-confirmation`, `POST /auth/sign-out`, `GET /config/public`, the auth routes) → 403 `age_confirmation_required`. A new route is gated without edits | 8.1.x, 8.2.1 (deny by default) | ST-068a | IT-04-06: parametrised over **every** `bola.MATRIX` route and every `/me/*` route with a pending sign-in → 403, never 2xx | D |
| T4-AG-3 | I/D | Pending sign-ins pile up (addresses held without an account) | Pending rows expire with the sign-in session TTL, at most 24 h (ADR 0006 abandoned-upload window as the analogue, judgment), and the purge pass deletes expired ones | 14.2.7; NFR-066 | ST-068a | IT: a pending row older than the TTL → gone after one pass | **O (SEC-S4-TM-04)** |
| T4-AG-4 | R | Someone answers `false`, then signs in again and answers `true` | **Accepted residual:** age is self-declared (OQ-05); keeping a record to block the retry would itself retain a minor's data (T4-AG-1). Footage of minors is handled by the capture-guide instruction, not by this gate | FR-003; ADR 0023 | ST-068a | — (stated in the interim wording) | Accepted residual |
| T4-AG-5 | T | `false` on an **existing** unconfirmed account deletes it by accident, or a CSRF triggers it | Origin check (403) and `SameSite` cookie as on `DELETE /me`; the deletion follows the `DELETE /me` path exactly (tombstone, session revocation, ADR 0042 purge). The UI asks for a second confirmation before sending `false` (PD-4 A-10/A-11) | 3.5.x CSRF; FR-007 | ST-068a, ST-068b | IT: foreign `Origin` → 403, account intact; `false` → same rows as IT-03-08 after a pass | D |

## 4. FR-008 video retention and purge (ST-069; ADR 0006, ADR 0042; flag `FEATURE_RETENTION_SETTING`)

| ID | STRIDE | Threat | Control (acceptance criterion) | ASVS / source | Story | Test | Status |
|---|---|---|---|---|---|---|---|
| T4-RT-1 | T/I | **Cross-account effect.** Ivy's `PUT /me/retention` (or a defect in the purge query) shortens or deletes Carlos's video | The setting is keyed by the session account only (no id in the route or body; closed body). The purge selects due review video by **joining each media row to its own owner's setting**; no global "days" value. Purge keys keep the ADR 0045 fail-closed shape check | 8.2.2; NFR-047; ADR 0045 | ST-069 | IT: Ivy 30 days, Carlos 365; `--now-offset-days 31` pass → only Ivy's review video gone, Carlos's object and row intact | D |
| T4-RT-2 | T | Purge order: rows deleted before the object leave an orphan object of identifiable people that no later pass finds | **Objects first, then the media row** (ADR 0042); a failed object delete keeps the row and retries next pass; tags, stats and plans stay (contract §5) | 14.2.7; NFR-066 (b) | ST-069 | IT: store fails the delete → row kept; next pass → object and row gone | D |
| T4-RT-3 | E | The dev/test clock option `--now-offset-days` purges production data early | Refused with exit 2 when `APP_ENV` ∈ {`staging`, `prod`}; not reachable from the API; logged | 13.x config; [AQS/SEC-12] | ST-069 | Unit: `APP_ENV=prod` + option → exit 2, nothing deleted | D |
| T4-RT-4 | I | Lengthening the window after the date passed "resurrects" a video, or a change applies to the past inconsistently | `review_video_delete_at` is recomputed from the current setting; a lengthened setting only keeps what is not yet purged. A purged object is gone (no undo). Copy says so (PM-4) | FR-008 | ST-069 | IT: purge, then `PUT 365` → still gone | D |
| T4-RT-5 | I | A signed media URL issued before the purge keeps playing | Bearer TTL ≤ 15 min (T-DL-10); residual accepted as in Sprint 3 | 14.2.1; NFR-055 | ST-069 | api-sprint-03 §4.3 | Accepted residual |

## 5. FR-009 training-data consent (ST-070; OQ-06; flag `FEATURE_TRAINING_CONSENT`)

| ID | STRIDE | Threat | Control (acceptance criterion) | ASVS / source | Story | Test | Status |
|---|---|---|---|---|---|---|---|
| T4-CS-1 | I | A match is used for training without opt-in (no row read as "yes", a lookup error read as "yes") | **Off by default:** no consent row = not consented. The label-set and gold-manifest builds read consent at build time via `racket.players.public` and **fail closed**: a lookup error aborts the build (no partial set), never includes the match | 14.2.x; [AQS/SEC-12]; ADR 0014 | ST-070 | Unit: missing row → excluded; port raises → build fails with no output; IT: two owners, one opted in → only that owner's matches in the set | D |
| T4-CS-2 | T | Revocation has no effect, or is said to apply sooner than it does | Revoke → excluded from the **next** label-set build; frozen gold-set versions are not edited and retire at their next scheduled refresh (OQ-06, ADR 0023). The copy states exactly this (PM-4) | FR-009 | ST-070 | IT: opt in, build v1 (included), revoke, build v2 → excluded; v1 unchanged | D |
| T4-CS-3 | R | No evidence of who consented when | One `training_consent_events` row per change (`account_id`, `opt_in`, `changed_at`); no IP, no user agent (data minimisation, judgment); same-value PUT writes nothing; events deleted with the account | 16.x audit [AQS/SEC-04] | ST-070 | IT: on, on, off → 2 events | D |
| T4-CS-4 | E | Consent set for another account, or by a labeller on someone else's match | Route takes no id; closed body; the build filters by the **match owner's** consent, never the labeller's | 8.2.2, 8.2.3 | ST-070 | IT (as T-BO-3): a labeller's consent does not include Ivy's match | D |

## 6. FR-160 / NFR-023 rate limit and storage quota (ST-072a; flag `FEATURE_QUOTAS`)

| ID | STRIDE | Threat | Control (acceptance criterion) | ASVS / source | Story | Test | Status |
|---|---|---|---|---|---|---|---|
| T4-QT-1 | D | Match-creation flood by one account | Key `match:create:<account_id>` 10 per 3600 s on `RateLimiter` (advisory lock per key, so parallel requests cannot share the last slot); counted after body validation; 429 with `retry_at`, nothing written | 2.4.1 [AQS/SEC-10]; NFR-023 | ST-072a | IT-04-09: 11th create → 429; 20 parallel creates → exactly 10 rows | D |
| T4-QT-2 | D/S | Many accounts from one host, or a spoofed `X-Forwarded-For` to rotate the IP key | Second key `match:create:ip:<ip>` 60 per 3600 s; IP from `players.domain.client_ip` with `TRUSTED_PROXY_HOPS` (rightmost trusted hop), never the raw left-most header value | 2.4.1; 13.x | ST-072a | IT: 61 creates from one IP over several accounts → 429; a forged XFF with hops = 1 does not change the key | D |
| T4-QT-3 | D | **Limiter or quota fails open** when its query errors or the DB is slow | Fail closed: an exception in the limiter or the usage query → 5xx `internal`, nothing written; no "allow on error" branch | [AQS/SEC-12]; ADR 0014 | ST-072a | Unit/IT: usage port raises → 503/500 and 0 rows | D |
| T4-QT-4 | D | **Quota bypass through tus resume or creation tricks** | Quota check 4a at upload creation counts live stored bytes + declared `Upload-Length` of open sessions. A `PATCH` can never exceed the declared length (`video_ingest/api.py:198`); `Upload-Length` is required (`service.py` `parse_upload_length`); `Upload-Defer-Length` and concatenation are not offered (`Tus-Extension: creation,checksum,expiration`). Resume is never re-counted and never adds headroom. Expired sessions stop counting at expiry | 5.2.4 (L3) [AQS/SEC-02]; NFR-023 | ST-072a | IT: at limit − 1 byte, create with length 2 → 429 `storage_quota_exceeded`; a resumed `PATCH` that sends a larger `Upload-Length` header → stored length unchanged and a chunk beyond it refused | D |
| T4-QT-5 | D | Race: two parallel creations each see room and together exceed the quota | Upload creation takes the account row lock (ADR 0045 "owned writes lock the account"), so check 4a and the insert are serialised per account | 5.2.4; 2.4.1 | ST-072a | IT: 10 parallel creations whose sum exceeds the limit → used ≤ limit after all | **O (SEC-S4-TM-05)** |
| T4-QT-6 | I | The 429 body leaks other accounts' or system-wide numbers | `quota` holds only the caller's `used_bytes`, `limit_bytes`, `requested_bytes`; `GET /me/quota` the caller's only | 8.2.2; 16.x | ST-072a | IT: body keys exactly as contract §7 (TCR row by QA for the error-body pin) | D |

## 7. NFR-022 billing alert rules: no secrets (ST-073)

| ID | STRIDE | Threat | Control (acceptance criterion) | ASVS / source | Story | Test | Status |
|---|---|---|---|---|---|---|---|
| T4-AL-1 | I | **A secret lands in a public repository** (P10): a webhook URL with a token, an API key, an account id with a billing scope, or an e-mail address in the rule files | Rules hold thresholds (50/80/100%), metric names and a **receiver name** only; the receiver's URL/token comes from an env var or secret mount at deploy time (`infra/env.example` lists the name with an empty value). No real address in git | 13.3.x secrets [AQS/SEC-06]; NFR-022 | ST-073 | CI secret scan clean on the PR; a test that parses the rule files and fails on `https?://`, `@`-addresses or key-shaped strings (≥ 20 chars base64/hex) outside an allowlist | D |
| T4-AL-2 | D/R | Alerts silently off: a missing receiver env var is ignored | Missing receiver at start → the alerting config refuses to load (fail closed) and logs the variable **name** only | [AQS/SEC-12] | ST-073 | Unit: rules load without the env var → error naming it | D |

## 8. BOLA matrix rows to add (backend/tests/regression/bola.py; IT-04-03; NFR-051)

Additions only (no existing row changes, so no TCR is needed for the add; QA confirms in the story PR). Carlos is signed in and probes Ivy's id; the owner's positive control runs **after** the attacker for state-changing routes, as for `DELETE /matches/{match_id}`. New `Probe.resource` kinds need a fixture: Ivy with one tagged match and a generated plan (ST-061b).

| Route | Kind | Attacker | Probe kwargs | Owner positive control | Story |
|---|---|---|---|---|---|
| `POST /me/plan/sessions/{session_id}/done` | `plan_session` | 404 | `{"headers": {"Idempotency-Key": "bola-probe-1"}}` (a valid key, so the 404 comes from ownership, not 422) | 200 | ST-062 |
| `DELETE /me/plan/sessions/{session_id}/done` | `plan_session` | 404 | `{}` | 200 | ST-062 |
| `POST /me/plan/assignments/{assignment_id}/swap` | `plan_assignment` | 404 | `{"json": {}}` | 200 or 409 `no_alternative` (not 404/405) | ST-062 |

Also, outside `MATRIX` (no path id; covered by their ITs): `POST/GET /me/plan` (IT-04-02: Carlos's `GET` never returns Ivy's plan), `POST /me/age-confirmation`, `GET/PUT /me/retention`, `GET/PUT /me/training-consent`, `GET /me/quota` (IT-04-06..09: 401 with no session; 404 with the flag off). `EXEMPT` stays empty. Extra IT cases for the matrix routes: Ivy's key replayed by Carlos → 404 (T4-PL-3); Ivy's own id from a replaced plan → 404 (T4-PL-1); with `FEATURE_AGE_GATE` on, a pending sign-in on every `MATRIX` route → 403 (T4-AG-2).

## 9. Findings and positions on PE-4 judgments

| ID | Severity | Finding / position | Owner | Resolution |
|---|---|---|---|---|
| SEC-S4-TM-01 | Should-fix | Plan generate and swap have no rate limit (T4-PL-6) | senior-backend-engineer | AC of ST-061b/ST-062; limits are settings |
| SEC-S4-TM-02 | Blocking (for ST-062) | Idempotency keys must be scoped per account, ownership before lookup (T4-PL-3) | senior-backend-engineer | AC of ST-062; red IT first |
| SEC-S4-TM-03 | Should-fix | Plan citations of a purged match outlive the deletion window (T4-PL-9) | senior-backend-engineer | AC of ST-061b (or a purge-pass step) |
| SEC-S4-TM-04 | Should-fix | Pending sign-ins need a TTL and purge (T4-AG-3) | senior-backend-engineer | AC of ST-068a |
| SEC-S4-TM-05 | Blocking (for ST-072a) | Quota check and upload insert must be serialised per account (T4-QT-5) | senior-backend-engineer | AC of ST-072a |
| SEC-S4-POS-01 | Position | **Confirmed:** `match:create:ip:<ip>` 60 per hour, as a second key next to the account key, with the IP from `client_ip` (T4-QT-2) | security-privacy-engineer | Contract §7 stands |
| SEC-S4-POS-02 | Position | **Confirmed with a condition:** `is_adult: false` on an existing unconfirmed account deletes it via the `DELETE /me` path; condition: Origin check and a second UI confirmation (T4-AG-5) | security-privacy-engineer | Contract §4 stands; PD-4 adds the confirm step |

## 10. Interim legal wording: not legal advice (US and AU)

**These notes are not legal advice, for the US or for AU.** They do not state that any US or AU law is satisfied. The values built in Sprint 4 (18+, consent off by default and revocable, ADR 0006 windows, default 90 days) are PO-accepted (ADR 0023); their legal adequacy and every user-facing text stay **interim, pending the NFR-070 legal review (P16)** by a qualified human before any real-user beta. Questions added to the Sprint 3 list (threat-model-sprint-03 §7):

| # | Jurisdiction | Question |
|---|---|---|
| Q-US-4 | US | Is a self-declared 18+ confirmation with no stored birth date enough for an adult-only service, and must we act differently when an under-13 person answers `false` (no data kept today)? |
| Q-AU-5 | AU | Is a consent event log of `account_id`, `opt_in`, `changed_at` adequate evidence of consent to training use, and how long may it be kept after withdrawal? |
| Q-B-3 | both | Is "excluded from the next build; frozen versions retire at the next scheduled refresh" an acceptable withdrawal effect for training use? |

## 11. Evidence (2026-10-17)

- `git -C /home/user/racket-analytics show origin/s04/pe-4-coaching-design-and-sprint-4-api-contrac:docs/architecture/api-sprint-04.md` → routes, §7 keys and §8 status table used above.
- `grep -n "offset + length > upload.length" backend/src/racket/video_ingest/api.py` → line 198; `grep -n "Tus-Extension" backend/src/racket/video_ingest/api.py` → `"creation,checksum,expiration"`.
- `grep -n "def client_ip" backend/src/racket/players/domain.py` → line 122 (trusted hops from the right).
- `grep -n "^EXEMPT" backend/tests/regression/bola.py` → `EXEMPT: dict[RouteKey, str] = {}`.
