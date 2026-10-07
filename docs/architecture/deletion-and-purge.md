# Design: deleting a match or an account, and the purge job

- **Status:** Accepted for build (principal-engineer, 2026-10-07, Sprint 3 review round 1, PE-R1S3-04 / task PE-3; amended in review round 2, below). The SEC-1 threat notes arrived in `af3dd99`; any further SEC item that changes this design amends it before ST-050 merges (its ticket PR is reviewed against this file, ADR 0039). Comments go under "Design review D3 (deletion-and-purge.md)" in `docs/sprints/03/review-rounds.md`.
- **Amended 2026-10-07 (review round 2, principal-engineer) for the SEC-1 threat notes** (`docs/security/threat-model-sprint-03.md` §8): SEC-S3-TM-01 / T-DL-3 (fail-closed key and prefix guards, §4.6), SEC-S3-TM-02 / T-DL-4 (no snapshot after a purge: tombstone-aware `FOR SHARE` and the orphan sweep, §4.2 and `analytics-snapshots.md` §4.2), SEC-S3-TM-05 / T-AC-2 (owned-row creation takes the account `FOR SHARE`; the pass tombstones every match of a tombstoned account, §3.3 and §4.2) and, in the same section, SEC-S3-TM-06 / T-AC-3 (read the address before nulling it, §3.2). Decision: ADR 0045. ST-050 and ST-051 code starts only from this version, test first (§6 rows marked **SEC**).
- **Decisions recorded as ADRs:** ADR 0042 (tombstone now, purge objects before rows, idempotent passes); ADR 0045 (fail-closed purge keys, lock-checked owned writes, orphan sweep; amends 0040 and 0042); ADR 0038 (the purge runs as its own scheduled Compose service with the app identity) is **Accepted** with this design.
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

One transaction. The account row lock comes **first**, before any match is read:

1. Session required (401 otherwise); body `{"confirm": "delete"}` exactly, else 422.
2. `SELECT … FROM accounts WHERE id = :me AND deleted_at IS NULL FOR UPDATE`. This waits for every in-flight owned-row creation of the account, because each one holds the account row `FOR SHARE` until it commits (§3.3). No row → 401 (already deleted).
3. Every match of the account, read **after** step 2 (under READ COMMITTED each statement takes a new snapshot, so a match whose creation committed while step 2 waited is included): step 3.1 (3)-(4) for each (tombstone, uploads closed); one `match.deleted` line each.
4. Read the account's `email` and `email_key`, then delete the unused `sign_in_links` and `sign_in_requests` for that address and key, so an old link cannot sign in to anything (SEC-S3-TM-06: this step comes **before** the address is nulled; the earlier text had it after, where it would find nothing).
5. `accounts.deleted_at = now()`; `accounts.email`, `email_key`, `username`, `display_name` set to `NULL` at once. The address is then free: a new magic-link sign-in with it creates a **new, empty account** (sprint-03 §3.4 ST-051 default; PM-1 may change it, §7).
6. Every `sessions` row of the account is deleted (signed out everywhere, FR-007; IT-03-08 two devices → both 401).
7. Log `account.deleted` with `user_id` only.
8. Commit; answer 202 with the sign-out headers of `POST /auth/sign-out` (cookie cleared, `Clear-Site-Data: "cache"`).

The account row stays as a tombstone with its `id` and `deleted_at` only, so the purge can find its matches; it holds no personal data from step 5 on.

### 3.3 Owned-row creation cannot outlive an account deletion (SEC-S3-TM-05, T-AC-2)

A request that authenticated before `DELETE /me` committed can still be running when it commits (`POST /matches`, `POST /matches/{id}/uploads`, the label commands of ST-052). Without a guard it commits a **live** match on a tombstoned account: nobody can sign in to it, nothing tombstones it, and `due_accounts` never sees "no match row left".

1. **Primary control: the account row `FOR SHARE`.** Every service method that inserts a row owned by an account (today: `matches` create, `upload_sessions` create, label session and label events; later any new owned root, context-map rule 4) first calls `racket.players.public.lock_live_account(session, account_id) -> bool` **in its own transaction**: `SELECT 1 FROM accounts WHERE id = :id AND deleted_at IS NULL FOR SHARE`. `False` → **401 `unauthenticated`** (the same answer as a revoked session, api-sprint-00) and nothing is written. The lock is held to the commit.
   - Create first: `DELETE /me` step 2 (`FOR UPDATE`) waits for the create's commit; step 3 then sees the new match and tombstones it.
   - Delete first: the create's `FOR SHARE` waits for `DELETE /me` to commit, then PostgreSQL re-checks the row (READ COMMITTED re-evaluates the `WHERE` on the new row version), finds `deleted_at` set, returns no row → 401, nothing written.
   - `racket.players.public` is a new port module of Identity & Players (context-map rule 1; R1 Open Host Service). It reads only the `accounts` row and returns a boolean.
2. **Second net: the pass tombstones what slipped through.** The pass starts with `players.public.tombstoned_account_ids(session)`; for each, `matches.public.tombstone_owned_by(session, account_id) -> list[match_id]` sets `deleted_at` on every **live** match of that owner and closes its uploads (§3.1 step 4), logging `match.deleted`. Those matches are then due in the same pass (§4.2). So even a write path that forgot step 1 cannot leave data on a deleted account for more than one interval, and `due_accounts` completes.
3. Scorebook commands and media uploads to an **existing** match need nothing new: they already lock the match row through the owner filter, which excludes tombstones (§3.1).

## 4. Purge (the job)

### 4.1 Entry point and identity

- **CLI:** `python -m racket.platform.purge --once` (module `racket.platform.purge`, `main(argv: list[str]) -> int`). `racket.platform` is the composition root here: the module holds no domain rules; it calls each context's `public` purge port in the order below. `--once` runs one pass and exits; there is no in-process loop (the scheduler of ADR 0038 repeats it).
- **Exit codes:** 0 the pass finished every due item; 1 at least one item failed and stays due (retried by the next pass); 2 usage or configuration error (bad arguments, no database, no store).
- **Runs in:** the `purge` Compose service (ADR 0038, Accepted): API image, the app Postgres role and the app S3 key, `edge` network, read-only root, `cap_drop: ALL`. Never in the `worker` service (ST-042 least privilege, NFR-054). On demand: `$DC exec -T purge python -m racket.platform.purge --once`. Schedule: `PURGE_INTERVAL_S`, default 86,400, refused above 86,400 (NFR-066 c).

### 4.2 One pass

```
pass():
  expire_abandoned_uploads()                       # §4.4, ST-038
  for account_id in players.public.tombstoned_account_ids():          # §3.3 (2), SEC-S3-TM-05
      matches.public.tombstone_owned_by(account_id)  # live matches of a deleted account become due now
  for match_id in due_matches():                    # tombstoned, oldest first, PURGE_BATCH (default 100)
      with claim(match_id) as claimed:              # SELECT … FOR UPDATE SKIP LOCKED on the tombstone row
          if not claimed: continue                  # another pass has it (IT-03-07 parallel)
          refs = video_ingest.public.object_refs(match_id)    # typed, shape-checked refs of THIS match only (§4.6)
          # an unsafe ref (bad shape, or a key another match also names) raises before ANY store call
          # for this match → purge.failed (stage objects, reason unsafe_ref), rows kept, next match
          for ref in refs: store.delete / delete_prefix / abort_multipart   # 404/NoSuchKey/NoSuchUpload = done
          # any store error → log purge.failed, rollback, leave every row, next match
          in ONE transaction:
              analytics.public.purge_match, dataset.public.purge_match,
              analysis_jobs.public.purge_match, video_ingest.public.purge_match,
              matches.public.purge_match            # root last; the FK cascade removes the scorebook
          log match.purged (match_id, user_id)
  sweep_orphan_snapshots()                          # SEC-S3-TM-02 second net, below
  for account_id in due_accounts():                 # tombstoned and no match row left (§3.3 makes this reachable)
      claim the same way; players.public.purge_account (sessions, roles, rate-limit keys, the row)
      log account.purged (user_id)
  log purge.pass (counts, failures, duration_ms); exit 0 or 1
```

- **Objects before rows** (ADR 0042). If an object delete fails, the rows that name it are still there, so the next pass lists it again (IT-03-07: "rows are never gone while their objects remain"; "no orphan"). The opposite order would need an outbox of keys to avoid orphans; it buys nothing here.
- **Idempotent.** Deleting a missing object or prefix is success; deleting rows already gone deletes 0 rows; a third pass is a no-op (IT-03-07). The claim is held only for one match's work, so two passes at once split the work and both exit 0 (IT-03-07 parallel case).
- **Store listing as a second net.** For each upload session the job deletes by prefix (`staging/<upload hex>/`), not only the keys the row lists, so a chunk written by a request that raced the delete is caught.
- **No snapshot after the purge (SEC-S3-TM-02, T-DL-4).** The after-commit recompute and read repair write a `metric_snapshots` row only while holding the match row `FOR SHARE` through a tombstone-aware port (`analytics-snapshots.md` §4.2 step 2). The tombstone write (`FOR UPDATE`) and the purge's row delete both conflict with that lock, so a recompute either commits **before** the tombstone (its row is then deleted by `analytics.public.purge_match` in the same pass as the match) or sees the tombstone and writes nothing. **Second net, `sweep_orphan_snapshots()`:** the pass reads `analytics.public.snapshot_match_ids(session, after, limit)` in pages, asks `matches.public.existing_ids(session, ids)` which of them still have a `matches` row (tombstoned or not), and calls `analytics.public.purge_match` for the rest, logging `purge.orphan_swept` (`kind=snapshot`, `match_id`). The composition root does the set difference; neither context reads the other's table (context-map rule 1).
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
| `purge.orphan_swept` | `kind` (`snapshot`), `match_id` |
| `purge.pass` | `matches`, `accounts`, `uploads`, `failed`, `duration_ms` |

Never a title, nickname, address, object key, consent reference or label value.

### 4.6 Fail-closed object keys (SEC-S3-TM-01, T-DL-3)

The purge runs with the app S3 key, which has `Admin` on the whole bucket (`infra/compose.yaml`, ADR 0038), so the store stops nothing. The guard is in code and fails **closed**:

1. **Typed refs, checked at construction (Capture & Media domain).** `video_ingest.public.object_refs(session, match_id)` returns only `OriginalKey`, `StagingPrefix` and `MultipartRef` values, built from the rows **of that match** (`WHERE match_id = :claimed`; never a store-wide listing). Each constructor checks the generated-name shape of `video_ingest/domain/uploads.py` with `re.fullmatch`:
   - `OriginalKey`: `originals/[0-9a-f]{32}`;
   - `StagingPrefix`: built from the upload id (`uuid.UUID`), never from a text column, as `staging/<uuid.hex>/`, and re-checked against `staging/[0-9a-f]{32}/`;
   - `MultipartRef`: an `OriginalKey` or a staging chunk key `staging/[0-9a-f]{32}/[0-9]{20}`, plus a non-empty upload id.
   A row whose key does not fit raises `UnsafeObjectRef`.
2. **No shared keys.** `object_refs` also checks that no row of **another** match names the same original key (`SELECT count(DISTINCT match_id) … WHERE object_key = :k` across `media_assets` and `upload_sessions`, both Capture & Media tables). More than one → `UnsafeObjectRef`.
3. **All refs first, then deletes.** The pass builds the whole ref list before its first store call. One `UnsafeObjectRef` → no store call for that match, `purge.failed` (`stage=objects`, `error=UnsafeObjectRef`), every row kept, `racket_purge_items_total{kind="match",result="refused"}`, next match. The item stays due and becomes `purge.overdue` after 6 days, so a human looks at it (§4.3). It is never "fixed" by deleting rows without their objects.
4. **Store-level guard (defence in depth, platform).** `ObjectStore.delete_prefix(prefix)` raises `UnsafeObjectKey` **before listing** unless `re.fullmatch(r"staging/[0-9a-f]{32}/", prefix)`; every key it lists must start with `prefix` or it stops. `ObjectStore.delete(key)` on the purge path is called only with a validated `OriginalKey` or chunk key. There is no other bulk delete in the code base, and none may be added without amending this section.

## 5. Ports this design adds (each in its own context)

| Port | Returns / does |
|---|---|
| `matches.public.owns_match` (changed) | excludes tombstoned matches |
| `matches.public.tombstone(session, match_id, owner_id) -> bool` | §3.1 step 3 (used by `DELETE /matches/{id}` and by `DELETE /me`) |
| `matches.public.due_for_purge(session, limit)`, `purge_match(session, match_id)` | §4.2 |
| `video_ingest.public.close_for_deleted_match`, `object_refs`, `purge_match`, `expire_abandoned(session, now, store)` | §3.1 step 4, §4.2, §4.4 |
| `analysis_jobs.public.purge_match`, `analytics.public.purge_match`, `dataset.public.purge_match` | delete own rows |
| `players.public.delete_account(session, account_id)`, `due_for_purge`, `purge_account` | §3.2, §4.2 |
| `platform.storage.ObjectStore.delete_prefix(prefix)` | new: shape check first (§4.6 (4)), then list + delete; missing = success |
| `video_ingest.domain` `OriginalKey`, `StagingPrefix`, `MultipartRef`, `UnsafeObjectRef` | §4.6 (1)-(2); `object_refs` returns only these |
| `players.public.lock_live_account(session, account_id) -> bool`, `tombstoned_account_ids(session)` | §3.3 (1)-(2); new module `racket/players/public.py` |
| `matches.public.tombstone_owned_by(session, account_id) -> list[UUID]`, `existing_ids(session, ids) -> set[UUID]` | §3.3 (2); orphan sweep |
| `matches.public.lock_live_sheet(session, match_id) -> (version, sheet) \| None` | `analytics-snapshots.md` §4.2 step 2 (`FOR SHARE`, tombstone-aware) |
| `analytics.public.snapshot_match_ids(session, after, limit)` | orphan sweep (§4.2) |

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
| **SEC** (T-DL-3) unit, red first: `delete_prefix("")`, `"staging/"`, `"originals/"`, `"staging/../x/"`, `"staging/<31 hex>/"`, `"staging/<32 HEX upper>/"`, `"staging/<hex>"` (no slash) → `UnsafeObjectKey`, and a spy client records **no** list and **no** delete call; the 32-hex form lists and deletes | BE, ST-050 (`tests/unit/platform/test_storage_delete_prefix.py`) |
| **SEC** (T-DL-3) unit: `OriginalKey`/`StagingPrefix`/`MultipartRef` refuse every bad shape above and `originals/` + 31 or 33 hex; pass plan with fakes: one unsafe ref → zero store calls for that match, rows kept, `purge.failed`, the next match is purged | BE, ST-050 |
| **SEC** (T-DL-3) IT: two owners, one match each with original, staging chunks and an open multipart upload; delete and purge owner 1 → owner 2's objects (store listing) and rows (inventory) are byte-for-byte intact. Same with a row of match 1 rewritten to name match 2's original key → the pass refuses match 1 (exit 1) and deletes nothing | senior-qa-engineer red (extends IT-03-06), BE green in ST-050 |
| **SEC** (T-DL-4) IT: commit a tag, hold the recompute (seam `replay_latest_event` called after `DELETE` and one pass) → no `metric_snapshots` row; a snapshot row inserted for a match id with no `matches` row → one pass → gone, `purge.orphan_swept` logged | senior-qa-engineer red (IT-03-02/IT-03-06), BE green in ST-046 + ST-050 |
| **SEC** (T-AC-2) IT: seam-insert a live match for an account after its tombstone → one pass → no row of that account; concurrency: 20 × (`POST /matches` ∥ `DELETE /me`) → after one pass, 0 live matches and 0 rows of the account; a create after the delete commit answers 401 | senior-qa-engineer red (IT-03-08, QA-FUZZ-3), BE green in ST-051 |
| **SEC** (T-AC-3) IT: a link requested before `DELETE /me` cannot reach the old account and no `sign_in_*` row is left for the address | senior-qa-engineer (IT-03-08), BE in ST-051 |
| unit (domain): tombstone rules; the pass plan (order objects → rows → root; account after matches) with fakes | BE, ST-050/051 |
| Compose: `purge` service identity, network, hardening, interval ≤ 86,400 | SRE-PURGE (b) config tests |

## 7. Open items (owner)

| Item | Owner | Default until answered |
|---|---|---|
| PM-1: may the address sign in again, and to what? | product-manager | a new, empty account (§3.2) |
| SEC-1 threat notes (ordering, revocation, logs, backups) | security-privacy-engineer | received (`af3dd99`); TM-01, -02, -05, -06 folded in on 2026-10-07 (ADR 0045); TM-03 (refused originals through the purge) and TM-04 (rate-limit retention) stay with senior-backend-engineer in ST-050 / ST-051 as routed |
| Legal adequacy of 1 min / 7 days / 24 h (NFR-070, OQ-05) | human PO with legal review | ADR 0006 interim values |
| FR-006 "plans keep a note 'evidence removed'" | Sprint 4 (no plans exist yet) | — |
| A dedicated purge DB role narrower than the app role | security-privacy-engineer | the app role (ADR 0038, judgment) |
