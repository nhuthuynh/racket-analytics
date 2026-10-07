# Design: deleting a match or an account, and the purge job

- **Status:** Accepted for build (principal-engineer, 2026-10-07, Sprint 3 review round 1, PE-R1S3-04 / task PE-3). The security-privacy-engineer's SEC-1 threat notes are still to come; any SEC-1 item that changes this design amends it before ST-050 merges (its ticket PR is reviewed against this file, ADR 0039). Comments go under "Design review D3 (deletion-and-purge.md)" in `docs/sprints/03/review-rounds.md`.
- **Decisions recorded as ADRs:** ADR 0042 (tombstone now, purge objects before rows, idempotent passes); ADR 0038 (the purge runs as its own scheduled Compose service with the app identity) is **Accepted** with this design.
- **Stories:** ST-050 (match), ST-051 (account), ST-038 (abandoned uploads on the same job), SRE-PURGE (b, c). HTTP contract: `api-sprint-03.md` §4.
- **Requirements:** FR-006, FR-007, FR-024; NFR-051, NFR-054, NFR-057, NFR-066 (a) hidden ≤ 1 min, (b) purged ≤ 7 days, (c) scheduled daily, (d) abandoned uploads freed ≤ 24 h after expiry; ADR 0006 (interim windows); [AQS/SEC-05] 14.2.7.

## 1. The decision in one paragraph

Deleting is two steps. **Hide** happens in the DELETE request's own transaction: the match (or the account and all its matches) gets a tombstone (`deleted_at`), every read path filters tombstoned rows out, and for an account every session is deleted at once. **Purge** is a separate, idempotent job, `python -m racket.platform.purge --once`, run by the `purge` Compose service at start and every `PURGE_INTERVAL_S` (≤ 86,400 s) and on demand. For each tombstoned match it deletes the **stored objects first** and the **database rows last**, each context through its own purge port, so a failure part-way always leaves rows that still point at every object left: no orphan, and the next pass finishes the job. Accounts are purged after all their matches. The same pass expires abandoned uploads (ST-038).

## 2. What data a match and an account own (inventory at `6f07640` + Sprint 3 tables)

| Owner context | Table / objects | Keyed by | Purged by |
|---|---|---|---|
| Match & Scoring | `matches` (root) | `id`, `owner_id` | `matches.public.purge_match` (last) |
| Match & Scoring | `match_participants`, `match_games`, `match_rallies`, `match_corrections` | `match_id` (FK `ON DELETE CASCADE`; corrections allow only the cascade, migration 0011) | the cascade from `matches` |
| Capture & Media | `upload_sessions` | `match_id`, `owner_id` | `video_ingest.public.purge_match` |
| Capture & Media | `media_assets`, `media_facts` | `match_id` (`media_facts` FK to `media_assets`) | `video_ingest.public.purge_match` |
| Capture & Media | objects `originals/<random>` (`media_assets.object_key`, `upload_sessions.object_key`), `staging/<upload hex>/…`, and open S3 multipart uploads (`upload_sessions.s3_upload_id`) | the rows above | `video_ingest.public.object_refs(match_id)` lists them; the job deletes them first |
| Vision Analysis | `jobs` | `match_id` (no FK) | `analysis_jobs.public.purge_match` |
| Analytics (new) | `metric_snapshots` | `match_id`, `owner_id` | `analytics.public.purge_match` |
| Dataset & Labelling (new) | label consent record, label session/events (ST-052) | `match_id` | `dataset.public.purge_match` |
| Identity & Players | `accounts` (root), `sessions` (FK cascade), labeller role rows (ST-052) | `account_id` | `players.public.purge_account` (after every match) |
| Identity & Players | `sign_in_links`, `sign_in_requests` | the address (`email`) and `email_key` | deleted **in the DELETE /me transaction** (§3.2) |
| Platform | `rate_limit_events` rows whose key ends with `:<account_id>` | the key text | `players.public.purge_account` calls `platform.ratelimit.forget(account_id)` |

Rules: a new table that holds a `match_id`, `owner_id` or `account_id` must get a line here and a purge port **in the same PR**; IT-03-06 and G03-03 read `information_schema` for those column names, so a missed table fails the test (sprint-03 risk row "Purge misses a table"). Cross-context foreign keys to `matches` are not added (context-map rule 1); each context deletes its own rows.

**Out of scope, with the reason** (for SEC-1 to confirm): process logs (they hold ids only, NFR-057, IT-03-13; retention is the platform's log retention); database backups and object-store versioning (none in the dev stack; the production backup and its expiry are a deployment item, ADR 0034, with the legal review NFR-070); gold-set copies already exported to the team's private bucket (BLK-GOLD-01, P11; consent withdrawal is FR-009, Sprint 4).

## 3. Hide (in the request)

### 3.1 `DELETE /matches/{match_id}` (ST-050)

One transaction, under the match row lock (`SELECT … FOR UPDATE` through the owner filter):

1. Owner filter: missing, not yours, malformed, or already deleted → 404 `not_found` (api-sprint-03 §4.1).
2. Body check: `{"confirm": "delete"}` exactly, else 422 (nothing written).
3. `matches.deleted_at = now()`, `matches.version` unchanged.
4. Capture & Media, through `video_ingest.public.close_for_deleted_match(session, match_id)`: a `receiving` upload session is set to `expired` and its stored file name is cleared (so a racing tus `PATCH`, which takes the same upload row lock, sees an expired session and stores nothing). Its staged bytes are left for the purge.
5. Log `match.deleted` with `match_id`, `user_id` (the owner's pseudonymous account id), nothing else (NFR-057).
6. Commit; answer 202 (api-sprint-03 §4.1).

From the commit on, **every** route that names the match answers 404 for its owner as for anyone else: match, list, media, uploads (`HEAD`/`PATCH /uploads/{id}` load the match through `matches.public.owns_match`, which excludes tombstones), score sheet and commands, stats, evidence, label routes. The single owner filter (`matches.repository` and `owns_match`) adds `deleted_at IS NULL`; there is no second place to forget (IT-03-06 calls every route after delete). A worker job that is running for the match finishes its current step; its writes go through ports that also check the tombstone (the probe stage's `media_facts` write is skipped for a tombstoned match) and the purge deletes the job row.

Hidden time: the same request, so NFR-066 (a) ≤ 1 min holds by construction; G03-02 (c) measures it.

### 3.2 `DELETE /me` (ST-051)

One transaction, under the account row lock:

1. Session required (401 otherwise); body `{"confirm": "delete"}` exactly, else 422.
2. Every match of the account: step 3.1 (3)-(4) for each (tombstone, uploads closed); one `match.deleted` line each.
3. `accounts.deleted_at = now()`; `accounts.email`, `email_key`, `username`, `display_name` set to `NULL` at once. The address is then free: a new magic-link sign-in with it creates a **new, empty account** (sprint-03 §3.4 ST-051 default; PM-1 may change it, §7).
4. Every `sessions` row of the account is deleted (signed out everywhere, FR-007; IT-03-08 two devices → both 401). Unused `sign_in_links` and `sign_in_requests` for the address are deleted, so an old link cannot sign in to anything.
5. Log `account.deleted` with `user_id` only.
6. Commit; answer 202 with the sign-out headers of `POST /auth/sign-out` (cookie cleared, `Clear-Site-Data: "cache"`).

The account row stays as a tombstone with its `id` and `deleted_at` only, so the purge can find its matches; it holds no personal data from step 3 on.

## 4. Purge (the job)

### 4.1 Entry point and identity

- **CLI:** `python -m racket.platform.purge --once` (module `racket.platform.purge`, `main(argv: list[str]) -> int`). `racket.platform` is the composition root here: the module holds no domain rules; it calls each context's `public` purge port in the order below. `--once` runs one pass and exits; there is no in-process loop (the scheduler of ADR 0038 repeats it).
- **Exit codes:** 0 the pass finished every due item; 1 at least one item failed and stays due (retried by the next pass); 2 usage or configuration error (bad arguments, no database, no store).
- **Runs in:** the `purge` Compose service (ADR 0038, Accepted): API image, the app Postgres role and the app S3 key, `edge` network, read-only root, `cap_drop: ALL`. Never in the `worker` service (ST-042 least privilege, NFR-054). On demand: `$DC exec -T purge python -m racket.platform.purge --once`. Schedule: `PURGE_INTERVAL_S`, default 86,400, refused above 86,400 (NFR-066 c).

### 4.2 One pass

```
pass():
  expire_abandoned_uploads()                       # §4.4, ST-038
  for match_id in due_matches():                    # tombstoned, oldest first, PURGE_BATCH (default 100)
      with claim(match_id) as claimed:              # SELECT … FOR UPDATE SKIP LOCKED on the tombstone row
          if not claimed: continue                  # another pass has it (IT-03-07 parallel)
          refs = video_ingest.public.object_refs(match_id)    # keys, staging prefixes, multipart ids
          for ref in refs: store.delete / delete_prefix / abort_multipart   # 404/NoSuchKey/NoSuchUpload = done
          # any store error → log purge.failed, rollback, leave every row, next match
          in ONE transaction:
              analytics.public.purge_match, dataset.public.purge_match,
              analysis_jobs.public.purge_match, video_ingest.public.purge_match,
              matches.public.purge_match            # root last; the FK cascade removes the scorebook
          log match.purged (match_id, user_id)
  for account_id in due_accounts():                 # tombstoned and no match row left
      claim the same way; players.public.purge_account (sessions, roles, rate-limit keys, the row)
      log account.purged (user_id)
  log purge.pass (counts, failures, duration_ms); exit 0 or 1
```

- **Objects before rows** (ADR 0042). If an object delete fails, the rows that name it are still there, so the next pass lists it again (IT-03-07: "rows are never gone while their objects remain"; "no orphan"). The opposite order would need an outbox of keys to avoid orphans; it buys nothing here.
- **Idempotent.** Deleting a missing object or prefix is success; deleting rows already gone deletes 0 rows; a third pass is a no-op (IT-03-07). The claim is held only for one match's work, so two passes at once split the work and both exit 0 (IT-03-07 parallel case).
- **Store listing as a second net.** For each upload session the job deletes by prefix (`staging/<upload hex>/`), not only the keys the row lists, so a chunk written by a request that raced the delete is caught.
- **No grace period.** A tombstoned match is due at once (`PURGE_MIN_AGE_S`, default 0). Undo of a deletion is not offered (the confirmation says it cannot be undone, FR-006).

### 4.3 Retries, the 7-day window and alerting

- A failed item is retried by every later pass. With a daily schedule, 7 days give at least 7 attempts.
- Each pass logs `purge.overdue` at ERROR for every tombstone older than `PURGE_ALERT_AFTER_S` (default 518,400 s = 6 days) and counts `racket_purge_overdue`. That is the alert before NFR-066 (b) is missed.
- Metrics: `racket_purge_runs_total{result}`, `racket_purge_items_total{kind,result}`, `racket_purge_duration_seconds`; one span per pass and per item (`OTEL_SERVICE_NAME=racket-purge`).

### 4.4 Abandoned uploads (ST-038, FR-024, NFR-066 d)

Same pass, first step: every `upload_sessions` row in `receiving` whose `expires_at` (api-sprint-01 §6.4) is past: abort its multipart upload, delete `staging/<upload hex>/`, then set `status = expired` and clear `file_name`. The row stays (HEAD/PATCH keep answering **410 `upload_expired`** to the owner and 404 to others, api-sprint-01 §6.4; IT-03-09 accepts 404 or 410); the match shows no upload in progress. Log `upload.expired` (`upload_id`, `match_id`, `user_id`). Freed within one interval of expiry, so ≤ 24 h with the daily default.

### 4.5 Log lines (NFR-057; IT-03-13)

| `event` | Fields besides `event`, `level`, `time`, `trace_id` |
|---|---|
| `match.deleted` | `match_id`, `user_id` |
| `account.deleted` | `user_id`, `matches` (count) |
| `match.purged` | `match_id`, `user_id`, `objects` (count), `rows` (count) |
| `account.purged` | `user_id` |
| `upload.expired` | `upload_id`, `match_id`, `user_id` |
| `purge.failed` | `kind` (`match` \| `account` \| `upload`), the id, `stage` (`objects` \| `rows`), `error` (exception class only) |
| `purge.overdue` | `kind`, the id, `age_s` |
| `purge.pass` | `matches`, `accounts`, `uploads`, `failed`, `duration_ms` |

Never a title, nickname, address, object key, consent reference or label value.

## 5. Ports this design adds (each in its own context)

| Port | Returns / does |
|---|---|
| `matches.public.owns_match` (changed) | excludes tombstoned matches |
| `matches.public.tombstone(session, match_id, owner_id) -> bool` | §3.1 step 3 (used by `DELETE /matches/{id}` and by `DELETE /me`) |
| `matches.public.due_for_purge(session, limit)`, `purge_match(session, match_id)` | §4.2 |
| `video_ingest.public.close_for_deleted_match`, `object_refs`, `purge_match`, `expire_abandoned(session, now, store)` | §3.1 step 4, §4.2, §4.4 |
| `analysis_jobs.public.purge_match`, `analytics.public.purge_match`, `dataset.public.purge_match` | delete own rows |
| `players.public.delete_account(session, account_id)`, `due_for_purge`, `purge_account` | §3.2, §4.2 |
| `platform.storage.ObjectStore.delete_prefix(prefix)` | new: list + delete; missing = success |

## 6. Tests (TDD order, negative first; already written red by QA where named)

| Case | Test |
|---|---|
| another account's match → 404, nothing changes | IT-03-06, IT-03-05 BOLA |
| no or wrong confirmation → 4xx, nothing written | IT-03-06, IT-03-08 |
| delete hides at once; every route 404; not listed | IT-03-06; G03-01 step 7 |
| second DELETE → 404 | IT-03-06 (`DELETE_OK` or 404) |
| purge leaves no row (information_schema inventory) and no object | IT-03-06; G03-03 (a, b) |
| store failure mid-purge: no orphan, rows kept, next pass completes, third pass no-op | IT-03-07 |
| two passes at once: both 0, nothing left | IT-03-07 |
| account: two devices signed out, purge leaves nothing, the other account's data untouched, the address signs in to a new empty account | IT-03-08; G03-01 step 8 |
| upload idle 23 h 59 kept; 24 h expired, bytes freed, 404/410; completed upload never expires | IT-03-09 |
| log lines hold ids only | IT-03-13 |
| unit (domain): tombstone rules; the pass plan (order objects → rows → root; account after matches) with fakes | BE, ST-050/051 |
| Compose: `purge` service identity, network, hardening, interval ≤ 86,400 | SRE-PURGE (b) config tests |

## 7. Open items (owner)

| Item | Owner | Default until answered |
|---|---|---|
| PM-1: may the address sign in again, and to what? | product-manager | a new, empty account (§3.2) |
| SEC-1 threat notes (ordering, revocation, logs, backups) | security-privacy-engineer | this design |
| Legal adequacy of 1 min / 7 days / 24 h (NFR-070, OQ-05) | human PO with legal review | ADR 0006 interim values |
| FR-006 "plans keep a note 'evidence removed'" | Sprint 4 (no plans exist yet) | — |
| A dedicated purge DB role narrower than the app role | security-privacy-engineer | the app role (ADR 0038, judgment) |
