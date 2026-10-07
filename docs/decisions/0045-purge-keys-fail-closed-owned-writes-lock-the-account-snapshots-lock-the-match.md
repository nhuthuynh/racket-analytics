# 0045. Purge deletes only shape-checked keys of the claimed match; owned writes lock the live account; snapshot writes lock the live match; the pass sweeps what slips through

- **Status:** Accepted (principal-engineer, 2026-10-07, Sprint 3 review round 2). Amends the consequences of ADR 0040 and ADR 0042. The security-privacy-engineer re-checks SEC-S3-TM-01, -02 and -05 against this ADR in the next review round.
- **Date:** 2026-10-07
- **Deciders:** principal-engineer
- **Consulted:** security-privacy-engineer (threat notes `docs/security/threat-model-sprint-03.md` T-DL-3, T-DL-4, T-AC-2, T-AC-3; findings SEC-S3-TM-01, -02, -05, -06); senior-backend-engineer (ST-046, ST-050, ST-051); senior-qa-engineer (red ITs)
- **Related:** `docs/architecture/deletion-and-purge.md` §3.2, §3.3, §4.2, §4.6, §5, §6; `docs/architecture/analytics-snapshots.md` §3 (S8), §4.2, §6; ADR 0038, ADR 0040, ADR 0042; context map rule 1 and R1; NFR-047, NFR-051, NFR-066 (b); [AQS/SEC-12]

## Context and problem statement

The SEC-1 threat notes (`af3dd99`) found three gaps in the accepted designs (review round 1 and round 2 findings SEC-S3-TM-01, -02, -05; QA's `open_defects.py` lists all three open):

1. **T-DL-3.** The purge runs with the app S3 key, which has `Admin` on the whole bucket. The design had `delete_prefix(prefix)` = list + delete and no check on the prefix or key. An empty or short prefix (`""`, `"staging/"`) or a key that another match also names deletes **other owners'** videos.
2. **T-DL-4.** ADR 0040's after-commit recompute upserts with a guard on `sheet_version` only. With no stored row the guard does not stop an insert, so a recompute that runs after `DELETE` and the purge inserts a `metric_snapshots` row for a match that no longer exists. Nothing finds it again, because the table has no foreign key (by design) and the match is no longer "due".
3. **T-AC-2.** A `POST /matches` (or upload create, or label command) that authenticated before `DELETE /me` committed can commit after it. That leaves a **live** match on a tombstoned account, which is never tombstoned, never purged, and blocks `due_accounts` ("no match row left") for good.

## Decision drivers

- A purge bug must fail **closed**. Deleting another user's data is worse than missing a delete (threat model §1).
- No orphan, ever (ADR 0042), including rows written by code that runs after the purge.
- Context-map rule 1: no context reads another's table. The composition root (`racket.platform.purge`) joins results of public ports.
- The simplest control that PostgreSQL already gives: row locks under READ COMMITTED (judgment, [AQS/ENG-04]).

## Considered options

1. **Code-level shape guards plus row locks plus a sweep in the pass** (chosen).
2. A scoped S3 key per prefix, or a bucket policy that denies deletes outside `originals/` and `staging/`. Rejected for R1: the dev store (SeaweedFS) has no per-prefix policies at the granularity needed. A prefix policy still allows deleting another owner's object under the same prefix. Kept as a non-dev hardening question for the security-privacy-engineer (threat model §8, "dedicated purge identity").
3. A foreign key from `metric_snapshots` and every owned table to `matches`/`accounts` with `ON DELETE CASCADE`. Rejected: it breaks context-map rule 1 (each context owns and deletes its own rows). It also does not stop the T-AC-2 insert, which happens before the account delete and is valid at the time.
4. `SERIALIZABLE` isolation for the create and delete transactions. Rejected: retry loops on every create path for one rare race, when a shared row lock gives the same ordering with no retries (judgment).

## Decision outcome

Chosen option: **1**.

1. **Fail-closed object keys (T-DL-3).** `video_ingest.public.object_refs` returns only typed refs (`OriginalKey` `originals/[0-9a-f]{32}`, `StagingPrefix` built from the upload UUID as `staging/<hex>/`, `MultipartRef`), built from the claimed match's own rows, each checked with `re.fullmatch` at construction. A key that another match's row also names is refused. The pass builds every ref before its first store call. One unsafe ref means no store call for that match, `purge.failed`, rows kept, item overdue at 6 days. `ObjectStore.delete_prefix` refuses any prefix that is not `staging/[0-9a-f]{32}/` before listing (defence in depth).
2. **Owned writes lock the live account (T-AC-2).** Every insert of an account-owned root first runs `players.public.lock_live_account` (`SELECT 1 FROM accounts WHERE id = :id AND deleted_at IS NULL FOR SHARE`) in its own transaction. On `False` it answers 401 and writes nothing. `DELETE /me` takes the account row `FOR UPDATE` **before** it reads the account's matches. The second net: each pass tombstones every live match of a tombstoned account (`players.public.tombstoned_account_ids` → `matches.public.tombstone_owned_by`).
3. **Snapshot writes lock the live match (T-DL-4).** The recompute and the read repair read the sheet through `matches.public.lock_live_sheet` (`FOR SHARE` on the match row, tombstone-aware). On `None` they write nothing. The second net: each pass deletes `metric_snapshots` rows whose `match_id` has no `matches` row (`analytics.public.snapshot_match_ids` against `matches.public.existing_ids`) and logs `purge.orphan_swept`.
4. **Address before nulling (T-AC-3, SEC-S3-TM-06).** `DELETE /me` deletes the `sign_in_*` rows for the address and `email_key` before it nulls them.
5. **Order of work.** ST-050 and ST-051 start from the amended design, test first: the red unit tests and ITs of `deletion-and-purge.md` §6 rows marked **SEC** come before the code. ST-046 implements S8 with its unit test.

## Pros and cons of the options

### Option 1
- Good: every control can be tested in isolation (unit for shapes, two-session IT for locks), needs no new infrastructure, and keeps each context deleting its own rows.
- Bad: one more port per context, and a scorebook command now waits for an in-flight recompute of the same match. That wait is one pure computation over at most 500 rallies; ST-046 measures it.

### Option 2
- Good: the store enforces the rule.
- Bad: not available in the dev store, and it does not separate owners within a prefix.

### Option 3
- Good: the database enforces the rule.
- Bad: it breaks context-map rule 1 and does not cover T-AC-2.

### Option 4
- Good: no explicit locks.
- Bad: retries on every create path.

## Consequences

- **Good:** an empty, short or foreign key can no longer reach the store. A recompute or a create that races a deletion either lands before the tombstone (and is purged with it) or writes nothing. Anything that slips through an unguarded path is removed within one pass.
- **Trade-offs accepted:** a refused purge item stays due until a human fixes the row. That is the overdue alert (§4.3), by design.
- **ADR 0040 amended:** "idempotent by the guarded upsert" now also needs the `FOR SHARE` read of §4.2 step 2. The `sheet_version` guard alone does not stop an insert after a purge.
- **ADR 0042 amended:** "no orphan" now covers rows written after the purge (snapshots) and owned rows created during an account deletion.
- **Follow-up work:** senior-qa-engineer writes the red ITs (`deletion-and-purge.md` §6 **SEC** rows). Senior-backend-engineer writes the red unit tests and the code in ST-046, ST-050 and ST-051. The security-privacy-engineer re-checks SEC-S3-TM-01, -02 and -05.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| The design had no guard and no lock | `grep -n 'FOR SHARE' docs/architecture/deletion-and-purge.md docs/architecture/analytics-snapshots.md` at `921ed53` → no match; `git log --oneline -- docs/architecture/deletion-and-purge.md` → `86d7839` only | data |
| The keys the guard accepts are the generated shapes | `backend/src/racket/video_ingest/domain/uploads.py:104` `f"originals/{uuid.uuid4().hex}"`, `:108` `f"staging/{upload_id.hex}/{offset:020d}"` | data |
| A scorebook command locks the match row | `backend/src/racket/matches/scorebook/repository.py:109-115` (`load(lock=True)` → `with_for_update()` on `matches`) | data |
| A `FOR SHARE` read that waits on a tombstone sees the tombstone and returns nothing | isolated Postgres 16.14 (`RA_DEV_STATE=<scratch>/pg-locks bash scripts/dev-postgres.sh start`): session 1 `SELECT … FOR UPDATE; UPDATE m SET deleted_at = now(); pg_sleep(2); COMMIT`, session 2 after 0.5 s `SELECT 1 FROM m WHERE id = 1 AND deleted_at IS NULL FOR SHARE` → `B rows=0` | test result |
| A tombstone waits for a held `FOR SHARE` | the same database: session 1 holds `FOR SHARE` for 2 s, session 2's `SELECT … FOR UPDATE; UPDATE …` → `tombstone waited 1.55 s` | test result |

## Confirmation

- The §6 **SEC** rows of `deletion-and-purge.md` exist as tests, red first, and are green when ST-046, ST-050 and ST-051 merge.
- `grep -rn "delete_prefix\|\.delete(" backend/src/racket` shows only the guarded store method and calls made with typed refs.
- The security-privacy-engineer closes SEC-S3-TM-01, -02 and -05 in `review-rounds.md`.
