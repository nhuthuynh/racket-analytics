# 0042. Deletion hides with a tombstone in the request; the purge deletes stored objects before database rows, in idempotent passes

- **Status:** Accepted (principal-engineer, 2026-10-07, Sprint 3 review round 1, PE-R1S3-04). SEC-1 threat notes (security-privacy-engineer) may amend it before ST-050 merges.
- **Date:** 2026-10-07
- **Deciders:** principal-engineer
- **Consulted:** security-privacy-engineer (SEC-1, pending), senior-backend-engineer (ST-050, ST-051, ST-038), sre-devops-engineer (ADR 0038), senior-qa-engineer (IT-03-06..09, IT-03-13)
- **Related:** `docs/architecture/deletion-and-purge.md`; `api-sprint-03.md` §4; ADR 0006, ADR 0038; FR-006, FR-007, FR-024; NFR-066, NFR-057, NFR-051; [AQS/SEC-05] 14.2.7

## Context and problem statement

FR-006/NFR-066 need a deleted match hidden within 1 minute and purged from the database and the object store within 7 days, with retries and idempotency, and FR-007 needs an account deletion that signs out every session. Rows and objects live in two systems with no shared transaction, so a failure between them can leave an object no row points to (an orphan nobody will ever delete) or a row pointing at nothing.

## Decision drivers

- No orphan, ever (IT-03-07: "rows are never gone while their objects remain").
- Hidden at once; purge retried until done; parallel passes safe (IT-03-07).
- Each context deletes only its own data (context-map rule 1).
- Least privilege: the purge does not run in the media sandbox (ST-042, ADR 0038).

## Considered options

1. **Tombstone in the request; purge objects first, then rows in one transaction per match** (chosen). The rows are the to-do list for the objects: while any object remains, the rows that name it remain.
2. **Rows first, with an outbox of object keys.** Good: the database is clean sooner. Bad: needs an outbox table and its own retry; the keys outlive the rows anyway, so nothing is gained for privacy.
3. **Hard delete everything in the request.** Good: no job. Bad: a store outage fails the user's delete or leaves orphans; a large video makes the request slow; no retry.
4. **Store lifecycle rules (bucket expiry by prefix/tag).** Good: no code for objects. Bad: needs per-object tagging at delete time (still a store call), is not portable across S3-compatible stores (SeaweedFS in dev), and gives no proof per match.

## Decision outcome

Option 1, with these rules (detail in deletion-and-purge.md):

1. `DELETE` sets `deleted_at` in the request; the single owner filter excludes tombstones, so every route answers 404 from the commit on. `DELETE /me` also deletes every session and clears the account's address and names in the same transaction.
2. `python -m racket.platform.purge --once` claims each due match with `FOR UPDATE SKIP LOCKED`, deletes its objects (missing = success; staging by prefix; multipart aborted), then deletes every context's rows through its `public` purge port in one transaction, the match root last. A store error leaves all rows; the next pass retries. Accounts are purged after their matches.
3. Exit codes 0/1/2; ids-only log lines `match.deleted`, `account.deleted`, `match.purged`, `account.purged`, `upload.expired`, `purge.failed`, `purge.overdue`, `purge.pass`.
4. Runs in the `purge` Compose service (ADR 0038, accepted with this ADR), daily by default and on demand.

### Consequences

- Every new table holding a `match_id`, `owner_id` or `account_id` needs a purge port in the same PR; the information-schema inventory (IT-03-06, G03-03) fails otherwise.
- No undo of a deletion (the confirmation says so).
- The `accounts` row stays as an id-only tombstone until its matches are purged.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Purge must leave no orphan and survive a store failure and parallel passes | `backend/tests/integration/test_it_03_07_purge_store_failure.py` | test (red until ST-050) |
| Every row and object gone after the purge | `test_it_03_06_delete_match_purge.py`, `test_it_03_08_delete_account.py`; scorecard G03-03 | test, method |
| Scorebook tables cascade from `matches`; corrections allow only the cascade | migrations `0009`, `0011` | code |
| Deletion of sensitive data on schedule | [AQS/SEC-05] 14.2.7; ADR 0006 | verified source, ADR |
| Option 1 over 2 | (judgment) | judgment |
